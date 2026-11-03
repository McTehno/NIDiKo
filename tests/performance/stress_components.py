"""Komponente za upravljanje vlog in nadzor preobremenitve stresnega testa.

Ta modul je ločen od Locust ogrodja, kar omogoča čisto testiranje logike
brez stranskih učinkov opičjega krpanja (monkey-patching) ali globalnega stanja.
"""
from collections import OrderedDict
import threading


class SlotManager:
    """Upravljalnik aktivnih mest za zagotavljanje točnih deležev vlog (40 % AI, 5 % glas).

    Ker Locust ob zmanjševanju števila uporabnikov lahko ustavi poljubna mesta,
    ohranjamo urejen seznam živih uporabnikov. Vsakemu aktivnemu mestu ob začetku
    reševanja določimo vlogo glede na njegov trenutni indeks med vsemi živimi mesti.
    Za vsak večkratnik 20 to zagotavlja natanko:
    - 5 % glasovnih mest (indeks % 20 == 0)
    - 40 % AI mest (indeks % 20 < 8)
    - 60 % običajnih mest (indeks % 20 >= 8)
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._users = OrderedDict()
        self._counter = 0

    def register(self, user):
        """Registracija novega uporabniškega mesta ob zagonu."""
        with self._lock:
            self._users[user] = self._counter
            self._counter += 1

    def unregister(self, user):
        """Odstranitev uporabniškega mesta ob zaustavitvi."""
        with self._lock:
            self._users.pop(user, None)

    def get_role(self, user):
        """Določitev trenutne vloge mesta glede na njegov položaj med aktivnimi mesti."""
        with self._lock:
            if user not in self._users:
                self._users[user] = self._counter
                self._counter += 1
            user_list = list(self._users.keys())
            rank = user_list.index(user)
            ai_user = (rank % 20 < 8)
            voice_user = (rank % 20 == 0)
            return rank, ai_user, voice_user

    def get_counts(self):
        """Izračun trenutnega števila aktivnih mest po vlogah."""
        with self._lock:
            total = len(self._users)
            ai_count = 0
            voice_count = 0
            for rank in range(total):
                if rank % 20 < 8:
                    ai_count += 1
                if rank % 20 == 0:
                    voice_count += 1
            ordinary_count = total - ai_count
            return {
                "active_users": total,
                "ordinary": ordinary_count,
                "ai": ai_count,
                "voice": voice_count,
            }


class OverloadMonitor:
    """Nadzornik preobremenitve po 1-minutnih oknih.

    Spremlja stopnjo napak v fiksnih oknih (privzeto 60 s).
    Preveri:
    1. Ali stopnja napak preseže 10 % v enem oknu (ob vsaj 20 zahtevah) -> takojšnja ustavitev.
    2. Ali stopnja napak preseže 5 % v dveh zaporednih oknih (ob vsaj 20 zahtevah) -> prehod v okrevanje.
    """

    def __init__(self, window_seconds, min_requests, consec_threshold, consec_windows, immediate_threshold, on_trigger=None):
        self.window_seconds = window_seconds
        self.min_requests = min_requests
        self.consec_threshold = consec_threshold
        self.consec_windows = consec_windows
        self.immediate_threshold = immediate_threshold
        self.on_trigger = on_trigger

        self.current_window_id = None
        self.window_total = 0
        self.window_failed = 0
        self.consecutive_bad_windows = 0
        self.triggered = False
        self.stop_reason = None
        self._lock = threading.Lock()

    def record_request(self, timestamp, ok, stage="unknown"):
        """Zabeleži izid zahteve in ob prehodu v novo okno ovrednoti pogoje ustavitve."""
        with self._lock:
            win_id = int(timestamp // self.window_seconds)
            if self.current_window_id is None:
                self.current_window_id = win_id

            # Če se je začelo novo časovno okno, ovrednotimo prejšnje
            if win_id != self.current_window_id:
                self._evaluate_window(self.current_window_id, self.window_total, self.window_failed, stage)
                self.current_window_id = win_id
                self.window_total = 0
                self.window_failed = 0

            self.window_total += 1
            if not ok:
                self.window_failed += 1

    def flush_window(self, stage="unknown"):
        """Eksplicitno ovrednoti trenutno okno (npr. ob koncu testa)."""
        with self._lock:
            if self.current_window_id is not None:
                self._evaluate_window(self.current_window_id, self.window_total, self.window_failed, stage)

    def _evaluate_window(self, win_id, total, failed, stage):
        """Preveri meje stopnje napak v zaključenem oknu."""
        if total < self.min_requests:
            return

        failure_fraction = failed / total

        # Pogoj 1: Več kot 10 % napak takoj sproži okrevanje
        if failure_fraction > self.immediate_threshold:
            self.triggered = True
            self.stop_reason = (
                f"Kritična preobremenitev: {failure_fraction * 100:.1f} % napak "
                f"v 1-minutnem oknu ({failed}/{total})"
            )
            if self.on_trigger:
                self.on_trigger(self.stop_reason, stage)
            return

        # Pogoj 2: Več kot 5 % napak v dveh zaporednih oknih
        if failure_fraction > self.consec_threshold:
            self.consecutive_bad_windows += 1
            if self.consecutive_bad_windows >= self.consec_windows:
                self.triggered = True
                self.stop_reason = (
                    f"Vztrajna preobremenitev: > {self.consec_threshold * 100:.0f} % napak "
                    f"v {self.consecutive_bad_windows} zaporednih oknih"
                )
                if self.on_trigger:
                    self.on_trigger(self.stop_reason, stage)
        else:
            self.consecutive_bad_windows = 0

