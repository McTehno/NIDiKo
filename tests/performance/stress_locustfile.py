"""Večstopenjski stresni test z dinamičnim razporejanjem vlog in nadzorom preobremenitve.

Zagon se izvaja prek scripts/run_stress.py. Scenarij ohranja enak uporabniški potek
kot vzdržljivostni test, vendar obremenitev stopnjuje po vnaprej določenih fazah ter
spremlja pogoje za predčasno ustavitev in okrevanje.
"""
import json
import os
import random
import time
from pathlib import Path
from urllib.parse import urlsplit

import gevent
import requests
from locust import HttpUser, LoadTestShape, events, task
from locust.exception import StopUser

from common import ROOT, answer_payload, load_stress_profile
from stress_components import OverloadMonitor, SlotManager

# Naložimo profil stresnega testa, delovno mapo in testne profile
PROFILE = load_stress_profile(os.environ["PERF_PROFILE"])
RUN = Path(os.environ["PERF_RUN_DIR"])
DATA = json.loads(Path(os.environ["PERF_DATA"]).read_text(encoding="utf-8"))
PROMPTS = json.loads((ROOT / "data/assistant-prompts.json").read_text(encoding="utf-8"))

# Globalni kazalci in tokovi
STREAM = None
NEXT_USER = 0

# Globalno stanje izvajanja obremenitve
STATE = {
    "stage": PROFILE["stages"][0]["name"],
    "phase": "ramp",
    "stage_index": 0,
    "early_stopped": False,
    "stop_reason": None,
    "in_recovery": False,
    "in_cooldown": False,
}


def record(kind, **values):
    """Zapiši strukturiran dogodek v events.jsonl z natančnim časovnim žigom."""
    global STREAM
    if STREAM and not STREAM.closed:
        try:
            STREAM.write(json.dumps({"kind": kind, "time": time.time(), **values}, ensure_ascii=False) + "\n")
            STREAM.flush()
        except (ValueError, IOError):
            pass


def on_monitor_trigger(reason, stage):
    """Klic ob zaznavi preobremenitve s strani OverloadMonitorja."""
    STATE["early_stopped"] = True
    STATE["stop_reason"] = reason
    record("early_stop_triggered", reason=reason, stage=stage)


SLOT_MANAGER = SlotManager()

MONITOR = OverloadMonitor(
    window_seconds=PROFILE["window_seconds"],
    min_requests=PROFILE["window_min_requests"],
    consec_threshold=PROFILE["stop_failure_rate_consecutive"],
    consec_windows=PROFILE["stop_consecutive_windows"],
    immediate_threshold=PROFILE["stop_failure_rate_immediate"],
    on_trigger=on_monitor_trigger,
)


@events.test_start.add_listener
def start(environment, **kwargs):
    """Inicializacija toka dogodkov ob začetku testa."""
    global STREAM
    STREAM = (RUN / "events.jsonl").open("x", encoding="utf-8")
    record("start", test_type="stress", stages=[s["name"] for s in PROFILE["stages"]])


@events.request.add_listener
def request_event(request_type, name, response_time, response_length,
                  exception, context=None, **kwargs):
    """Zapis vsake zahteve s pripadajočo fazo in posredovanje monitorju."""
    now = time.time()
    ok = (exception is None)
    record("request", group=name, ms=response_time, ok=ok,
           stage=STATE["stage"], phase=STATE["phase"],
           cached=(context or {}).get("cached"))
    MONITOR.record_request(now, ok, stage=STATE["stage"])


@events.test_stop.add_listener
def stop(environment, **kwargs):
    """Zaključek testiranja in zaprtje toka."""
    global STREAM
    if STREAM and not STREAM.closed:
        MONITOR.flush_window(stage=STATE["stage"])
        record("stop", **STATE)
        try:
            STREAM.close()
        finally:
            STREAM = None


@events.user_error.add_listener
def user_error(user_instance, exception, tb, **kwargs):
    """Beleženje neobravnavanih napak uporabniškega poteka."""
    record("fatal", reason="Neobravnavana napaka uporabniškega poteka; preveri run.log.")


class StressShape(LoadTestShape):
    """Večstopenjska oblika obremenitve z avtomatskim prehodom in predčasno ustavitvijo."""

    def __init__(self):
        super().__init__()
        self.stages = PROFILE["stages"]
        self.current_idx = 0
        self.is_ramping = True
        self.steady_start = None
        self.steady_end = None

        # Indeksi posebnih faz
        self.recovery_idx = next((i for i, s in enumerate(self.stages) if s.get("is_recovery")), None)
        self.cooldown_idx = next((i for i, s in enumerate(self.stages) if s.get("is_cooldown")), None)

    def tick(self):
        now = time.time()
        counts = SLOT_MANAGER.get_counts()
        current_users = self.get_current_user_count()

        # 1. Preverjanje predčasne ustavitve: prehod v okrevanje ob preobremenitvi
        if STATE["early_stopped"] and not STATE["in_recovery"] and not STATE["in_cooldown"]:
            if self.recovery_idx is not None and self.current_idx < self.recovery_idx:
                record("transition_to_recovery", reason=STATE["stop_reason"],
                       from_stage=self.stages[self.current_idx]["name"], time=now)
                self.current_idx = self.recovery_idx
                self.is_ramping = True
                self.steady_start = None
                self.steady_end = None
                STATE["in_recovery"] = True
                STATE["stage"] = self.stages[self.current_idx]["name"]

        # 2. Če smo zaključili vse stopnje, zaključimo test
        if self.current_idx >= len(self.stages):
            return None

        current_stage = self.stages[self.current_idx]
        target_users = current_stage["users"]
        spawn_rate = PROFILE["spawn_rate"]
        stage_name = current_stage["name"]
        is_warmup = current_stage.get("is_warmup", False)
        is_recovery = current_stage.get("is_recovery", False)
        is_cooldown = current_stage.get("is_cooldown", False)

        if is_recovery:
            STATE["in_recovery"] = True
        if is_cooldown:
            STATE["in_cooldown"] = True

        STATE["stage"] = stage_name
        STATE["stage_index"] = self.current_idx

        # 3. Faza prehajanja (dodajanje ali zmanjševanje mest do ciljne populacije)
        if self.is_ramping:
            if current_users == target_users:
                self.is_ramping = False
                self.steady_start = now
                self.steady_end = now + current_stage["duration_seconds"]
                STATE["phase"] = ("warmup" if is_warmup else
                                  "recovery" if is_recovery else
                                  "cooldown" if is_cooldown else "steady")
                record("stage_start", stage=stage_name, users=target_users,
                       steady_start=self.steady_start, steady_end=self.steady_end,
                       stage_index=self.current_idx)
            else:
                STATE["phase"] = "ramp"
                record("population", users=current_users, target=target_users,
                       stage=stage_name, phase="ramp", **counts)
                return target_users, spawn_rate

        # 4. Stabilna faza trenutne stopnje
        if not self.is_ramping:
            if now < self.steady_end:
                STATE["phase"] = ("warmup" if is_warmup else
                                  "recovery" if is_recovery else
                                  "cooldown" if is_cooldown else "steady")
                record("population", users=current_users, target=target_users,
                       stage=stage_name, phase=STATE["phase"], **counts)
                return target_users, spawn_rate
            else:
                # Čas trenutne stopnje je potekel -> prehod v naslednjo stopnjo
                record("stage_end", stage=stage_name, stage_index=self.current_idx,
                       duration=current_stage["duration_seconds"])
                self.current_idx += 1
                self.is_ramping = True
                self.steady_start = None
                self.steady_end = None

                if self.current_idx >= len(self.stages):
                    return None

                next_stage = self.stages[self.current_idx]
                STATE["stage"] = next_stage["name"]
                STATE["stage_index"] = self.current_idx
                return next_stage["users"], spawn_rate

        return target_users, spawn_rate


class StressQuestionnaireUser(HttpUser):
    """Uporabnik za izvajanje vprašalnika z dinamičnim določanjem vloge in premori."""

    def on_start(self):
        """Ob zagonu mesta se registriramo v SlotManager za točno porazdelitev vlog."""
        SLOT_MANAGER.register(self)
        self.rng = random.Random(PROFILE["seed"] + id(self))

    def on_stop(self):
        """Ob zaustavitvi mesta se odjavimo iz SlotManagerja."""
        SLOT_MANAGER.unregister(self)

    def pause(self, key):
        """Simulacija premora človeškega branja z naključnim intervalom."""
        gevent.sleep(self.rng.uniform(*PROFILE[key]))

    def call(self, method, path, group, validator, **kwargs):
        """Klic API-ja z validacijo odgovora in varnim skrivanjem občutljivih podatkov."""
        with self.client.request(method, path, name=group, catch_response=True,
                                 timeout=PROFILE["timeout_seconds"], **kwargs) as response:
            try:
                value = response.json()
                valid = (response.status_code == 200 and validator(value))
            except (ValueError, KeyError, TypeError, AttributeError):
                value, valid = None, False

            if not valid:
                response.failure(f"Neveljaven odgovor skupine {group}; HTTP {response.status_code}")
                return None

            if group == "voice_api":
                response.request_meta["context"]["cached"] = value.get("cached")
            response.success()
            return value

    @task
    def questionnaire(self):
        """Izvedba celotnega reševanja enega vprašalnika z dodeljenim sintetičnim profilom."""
        global NEXT_USER
        if NEXT_USER >= len(DATA["user_ids"]):
            record("fatal", reason="Zmanjkalo je ločenih testnih profilov.")
            self.environment.process_exit_code = 2
            gevent.spawn(self.environment.runner.quit)
            raise StopUser()

        user_id = DATA["user_ids"][NEXT_USER]
        NEXT_USER += 1

        # Vlogo določimo dinamično glede na trenutno populacijo
        rank, ai_user, voice_user = SLOT_MANAGER.get_role(self)
        target = self.rng.choice(DATA["targets"])
        current_stage = STATE["stage"]
        record("journey_start", ai=ai_user, voice=voice_user, stage=current_stage, rank=rank)

        questionnaire = self.call(
            "GET", "/api/questionnaires", "ordinary/questionnaire",
            lambda v: (v.get("target_id") == target["target_id"] and
                       v.get("target_type") == target["target_type"] and
                       bool(v.get("questions")) and
                       all(q.get("id") and q.get("question") and q.get("type", "yes_no") == "yes_no"
                           for q in v["questions"])),
            params={**target, "user_id": user_id}
        )

        if not questionnaire:
            self.pause("think_seconds")
            return

        questions = questionnaire["questions"]
        ai_count = self.rng.choices(PROFILE["ai_counts"], PROFILE["ai_weights"])[0] if ai_user else 0
        ai_indices = sorted(self.rng.randrange(len(questions)) for _ in range(ai_count))
        voice_index = self.rng.randrange(len(questions)) if voice_user else -1

        session_id = None
        answers = []

        for index, question in enumerate(questions):
            self.pause("think_seconds")
            context = {
                key: question.get(key) or
                     (target["target_id"] if target["target_type"] == key.removesuffix("_id") else None)
                for key in ("learning_path_id", "module_id", "learning_unit_id")
            }

            # Sporočila besedilnega AI pomočnika
            for _ in range(ai_indices.count(index)):
                result = self.call(
                    "POST", "/api/assessment-assistant/message", "ai",
                    lambda v: bool(v.get("session_id")) and isinstance(v.get("answer"), str) and bool(v["answer"].strip()),
                    json={**context, "session_id": session_id, "user_id": user_id,
                          "question_id": question["id"], "question_text": question["question"],
                          "answer_options": ["Da", "Ne"], "user_message": self.rng.choice(PROMPTS)}
                )
                if result:
                    session_id = result.get("session_id")
                self.pause("assistant_read_seconds")

            # Glasovna pomoč (enkrat na celotno reševanje za izbrana mesta)
            if index == voice_index:
                result = self.call(
                    "POST", "/api/voice-help/question", "voice_api",
                    lambda v: isinstance(v.get("cached"), bool) and bool(v.get("help_text")) and bool(v.get("audio_url")),
                    json={**target, "question_id": question["id"], "question_text": question["question"],
                          "answer_options": ["Da", "Ne"], "locale": "sl-SI", "voice_name": "sl-SI-PetraNeural"}
                )
                if result:
                    audio = urlsplit(result.get("audio_url", ""))
                    if audio.scheme == "https" and audio.hostname in DATA["audio_hosts"]:
                        started = time.perf_counter()
                        error = None
                        size = 0
                        try:
                            # Ločena seja brez shranjevanja podpisanega naslova v primeru napake
                            with requests.Session() as audio_client:
                                response = audio_client.get(
                                    result["audio_url"], allow_redirects=False,
                                    timeout=PROFILE["timeout_seconds"]
                                )
                                size = len(response.content)
                                if (response.status_code != 200 or not size or
                                        not response.headers.get("Content-Type", "").startswith("audio/")):
                                    error = RuntimeError("Zvočni posnetek ni dosegljiv.")
                        except requests.RequestException:
                            error = RuntimeError("Prenos zvočnega posnetka ni uspel.")

                        duration_ms = (time.perf_counter() - started) * 1000
                        self.environment.events.request.fire(
                            request_type="GET", name="voice_audio",
                            response_time=duration_ms, response_length=size,
                            exception=error, context={}
                        )
                        record("voice_delivery", cached=result.get("cached"), ms=duration_ms, stage=STATE["stage"])
                    else:
                        record("fatal", reason="Zvočni naslov ni na dovoljenem seznamu.")
                    self.pause("assistant_read_seconds")

            answer = answer_payload(question)
            answer.update(context)
            answer["answer"] = self.rng.choice([True, False])
            answers.append(answer)

        # Oddaja vseh odgovorov naenkrat
        result = self.call(
            "POST", "/api/assessments/evaluate", "ordinary/evaluate",
            lambda v: (v.get("user_id") == user_id and
                       v.get("target_id") == target["target_id"] and
                       v.get("target_type") == target["target_type"] and
                       isinstance(v.get("learning_unit_results"), list)),
            json={**target, "user_id": user_id, "answers": answers}
        )
        record("journey_end", ok=(result is not None), ai_messages=ai_count, stage=current_stage)
