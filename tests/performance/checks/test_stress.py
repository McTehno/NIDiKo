"""Preverjanja za večstopenjski stresni test NIDiKo.

Vključuje:
1. Validacijo konfiguracijskih profilov in izračuna trajanja.
2. Preverjanje točne porazdelitve vlog (40 % AI, 5 % glas) pri povečevanju in zmanjševanju populacije.
3. Preizkus pogojev za predčasno ustavitev (OverloadMonitor: > 10 % v 1 oknu, > 5 % v 2 oknih).
4. Sintetični preizkus analize stresnega testa (analyze_stress.py).
5. Integracijski zagon pravega Locusta proti lokalnemu MockAPI.
"""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from common import load_stress_profile, stress_duration
from stress_components import OverloadMonitor, SlotManager

spec = importlib.util.spec_from_file_location("analyze_stress", ROOT / "scripts/analyze_stress.py")
analyze_stress = importlib.util.module_from_spec(spec)
spec.loader.exec_module(analyze_stress)


class MockAPI(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def send_json(self, value):
        payload = json.dumps(value).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        self.send_json({
            "target_type": "learning_path",
            "target_id": "path1",
            "questions": [{"id": "q1", "question": "Poznate osnove?", "type": "yes_no"}],
        })

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        data = json.loads(self.rfile.read(length)) if length > 0 else {}
        if self.path.endswith("evaluate"):
            self.send_json({
                "user_id": data.get("user_id"),
                "target_id": data.get("target_id"),
                "target_type": data.get("target_type"),
                "learning_unit_results": [],
            })
        elif self.path.endswith("message"):
            self.send_json({"session_id": "mock-session", "answer": "Razlaga vprašanja."})
        else:
            self.send_json({
                "cached": True,
                "help_text": "Pomoč",
                "audio_url": "https://audio.example.invalid/test.mp3",
            })


class StressProfileAndDurationChecks(unittest.TestCase):
    def test_load_default_stress_profile(self):
        profile = load_stress_profile(ROOT / "profiles/stress.json")
        self.assertEqual(len(profile["stages"]), 10)
        self.assertEqual(profile["spawn_rate"], 2)
        self.assertEqual(profile["stages"][0]["name"], "warmup")
        self.assertEqual(profile["stages"][7]["name"], "stage_7")
        self.assertEqual(profile["stages"][7]["users"], 220)
        self.assertEqual(profile["stages"][8]["name"], "recovery")
        self.assertEqual(profile["stages"][8]["users"], 20)
        self.assertEqual(profile["stages"][9]["name"], "cooldown")
        self.assertEqual(profile["stages"][9]["users"], 0)

        # Preverimo ocenjeno skupno trajanje (približno 90 minut = 5440 s)
        total_sec = stress_duration(profile)
        self.assertGreaterEqual(total_sec, 5200)
        self.assertLessEqual(total_sec, 5600)

    def test_invalid_profile_rejections(self):
        bad_profile = {
            "spawn_rate": 2, "timeout_seconds": 60, "window_seconds": 60,
            "window_min_requests": 20, "stop_failure_rate_consecutive": 0.05,
            "stop_consecutive_windows": 2, "stop_failure_rate_immediate": 0.10,
            "stages": [{"name": "bad", "users": 25, "duration_seconds": 60}],
            "think_seconds": [15, 35], "assistant_read_seconds": [10, 25],
            "ai_counts": [1], "ai_weights": [10],
        }
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as tf:
            tf.write(json.dumps(bad_profile))
            tf_path = tf.name
        try:
            with self.assertRaises(ValueError):
                load_stress_profile(tf_path)
        finally:
            os.remove(tf_path)


class SlotManagerRoleChecks(unittest.TestCase):
    def test_proportions_across_scale_up_and_down(self):
        manager = SlotManager()
        users = [f"mock_user_{i}" for i in range(220)]

        # 1. 20 uporabnikov: natanko 8 AI, 1 glas, 12 navadnih
        for u in users[:20]:
            manager.register(u)
        counts20 = manager.get_counts()
        self.assertEqual(counts20["active_users"], 20)
        self.assertEqual(counts20["ai"], 8)
        self.assertEqual(counts20["voice"], 1)
        self.assertEqual(counts20["ordinary"], 12)

        # 2. Povečanje na 100 uporabnikov: 40 AI, 5 glasovnih, 60 navadnih
        for u in users[20:100]:
            manager.register(u)
        counts100 = manager.get_counts()
        self.assertEqual(counts100["active_users"], 100)
        self.assertEqual(counts100["ai"], 40)
        self.assertEqual(counts100["voice"], 5)
        self.assertEqual(counts100["ordinary"], 60)

        # 3. Povečanje na 220 uporabnikov: 88 AI, 11 glasovnih, 132 navadnih
        for u in users[100:220]:
            manager.register(u)
        counts220 = manager.get_counts()
        self.assertEqual(counts220["active_users"], 220)
        self.assertEqual(counts220["ai"], 88)
        self.assertEqual(counts220["voice"], 11)
        self.assertEqual(counts220["ordinary"], 132)

        # 4. Zmanjšanje obremenitve nazaj na 20 uporabnikov (simulacija okrevanja)
        # Odstranimo poljubnih 200 uporabnikov
        for u in users[20:]:
            manager.unregister(u)
        counts_recovery = manager.get_counts()
        self.assertEqual(counts_recovery["active_users"], 20)
        self.assertEqual(counts_recovery["ai"], 8)
        self.assertEqual(counts_recovery["voice"], 1)
        self.assertEqual(counts_recovery["ordinary"], 12)

        # Preverimo tudi vloge posameznih preživelih uporabnikov
        for i, u in enumerate(users[:20]):
            rank, ai, voice = manager.get_role(u)
            self.assertEqual(rank, i)
            self.assertEqual(ai, (i < 8))
            self.assertEqual(voice, (i == 0))


class OverloadMonitorChecks(unittest.TestCase):
    def test_immediate_stop_trigger(self):
        triggered_info = []

        def on_trig(reason, stage):
            triggered_info.append((reason, stage))

        monitor = OverloadMonitor(
            window_seconds=60, min_requests=20,
            consec_threshold=0.05, consec_windows=2, immediate_threshold=0.10,
            on_trigger=on_trig
        )
        # Okno 16 (od 960 do 1019 s):
        for _ in range(17):
            monitor.record_request(1000, ok=True, stage="stage_3")
        for _ in range(3):
            monitor.record_request(1005, ok=False, stage="stage_3")  # 3/20 = 15 % napak (> 10 %)

        # Začetek okna 17 (1020 do 1079 s) sproži ovrednotenje okna 16
        monitor.record_request(1025, ok=True, stage="stage_3")
        self.assertTrue(monitor.triggered)
        self.assertIn("15.0 % napak", monitor.stop_reason)
        self.assertEqual(len(triggered_info), 1)
        self.assertEqual(triggered_info[0][1], "stage_3")

    def test_consecutive_stop_trigger(self):
        triggered_info = []

        def on_trig(reason, stage):
            triggered_info.append((reason, stage))

        monitor = OverloadMonitor(
            window_seconds=60, min_requests=20,
            consec_threshold=0.05, consec_windows=2, immediate_threshold=0.15,
            on_trigger=on_trig
        )
        # Okno 33 (1980..2039 s): 2 napaki od 25 zahtev = 8 % napak (> 5 %, a < 15 %)
        for _ in range(23):
            monitor.record_request(2000, ok=True, stage="stage_4")
        for _ in range(2):
            monitor.record_request(2010, ok=False, stage="stage_4")

        # Prehod v okno 34 (2040..2099 s)
        monitor.record_request(2045, ok=True, stage="stage_4")
        self.assertFalse(monitor.triggered)
        self.assertEqual(monitor.consecutive_bad_windows, 1)

        # Okno 34: ponovno 2 napaki od 25 zahtev = 8 % napak
        for _ in range(22):
            monitor.record_request(2050, ok=True, stage="stage_4")
        for _ in range(2):
            monitor.record_request(2055, ok=False, stage="stage_4")

        # Prehod v okno 35 (2100..2159 s) sproži ustavitev zaradi 2 zaporednih oken
        monitor.record_request(2105, ok=True, stage="stage_4")
        self.assertTrue(monitor.triggered)
        self.assertIn("2 zaporednih", monitor.stop_reason)
        self.assertEqual(len(triggered_info), 1)


class SyntheticStressAnalysisChecks(unittest.TestCase):
    def test_synthetic_stages_analysis(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            run = Path(tmp_dir)
            profile = {
                "spawn_rate": 2,
                "stages": [
                    {"name": "warmup", "users": 20, "duration_seconds": 10, "is_warmup": True},
                    {"name": "stage_1", "users": 20, "duration_seconds": 20},
                    {"name": "recovery", "users": 20, "duration_seconds": 20, "is_recovery": True},
                ],
                "ordinary_ms": 400, "ai_ms": 7000, "voice_ms": 3000,
                "ordinary_fast_fraction": 0.99, "success_fraction": 0.999,
                "minimum_samples_per_group": 10,
            }
            manifest = {
                "run_id": "TEST_STRESS",
                "test_type": "stress",
                "command_completed": True,
                "profile": profile,
            }
            (run / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

            # Simuliramo dogodke za stage_1 in recovery
            events = [
                {"kind": "start"},
                {"kind": "stage_start", "stage": "warmup", "time": 10, "users": 20},
                {"kind": "stage_end", "stage": "warmup", "time": 20},
                {"kind": "stage_start", "stage": "stage_1", "time": 20, "users": 20},
                {"kind": "population", "stage": "stage_1", "phase": "steady", "users": 20, "ordinary": 12, "ai": 8, "voice": 1, "time": 21},
            ]
            for i in range(50):
                events.append({"kind": "request", "stage": "stage_1", "phase": "steady", "group": "ordinary/questionnaire", "ms": 150, "ok": True, "time": 22})
                events.append({"kind": "request", "stage": "stage_1", "phase": "steady", "group": "ai", "ms": 1200, "ok": True, "time": 23})
            events.extend([
                {"kind": "stage_end", "stage": "stage_1", "time": 40},
                {"kind": "stage_start", "stage": "recovery", "time": 40, "users": 20},
                {"kind": "population", "stage": "recovery", "phase": "recovery", "users": 20, "ordinary": 12, "ai": 8, "voice": 1, "time": 41},
            ])
            for i in range(50):
                events.append({"kind": "request", "stage": "recovery", "phase": "recovery", "group": "ordinary/questionnaire", "ms": 160, "ok": True, "time": 42})
                events.append({"kind": "request", "stage": "recovery", "phase": "recovery", "group": "ai", "ms": 1300, "ok": True, "time": 43})
            events.extend([
                {"kind": "stage_end", "stage": "recovery", "time": 60},
                {"kind": "stop", "time": 61},
            ])

            (run / "events.jsonl").write_text("".join(json.dumps(e) + "\n" for e in events), encoding="utf-8")

            summary = analyze_stress.analyze(run)
            self.assertEqual(summary["status"], "PASS")
            self.assertEqual(summary["highest_tested_stage"], "stage_1")
            self.assertTrue((run / "summary.json").exists())
            self.assertTrue((run / "report.html").exists())
            self.assertIn("stage_1", [s["name"] for s in summary["stages"]])
            self.assertIn("recovery", [s["name"] for s in summary["stages"]])


@unittest.skipUnless(importlib.util.find_spec("locust"), "Locust ni nameščen")
class StressLocustMockRuntimeCheck(unittest.TestCase):
    def test_real_locust_stress_against_mock_api(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), MockAPI)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            with tempfile.TemporaryDirectory() as directory:
                run = Path(directory)
                profile = {
                    "spawn_rate": 20,
                    "stages": [
                        {"name": "warmup", "users": 20, "duration_seconds": 2, "is_warmup": True},
                        {"name": "stage_1", "users": 20, "duration_seconds": 3},
                        {"name": "stage_2", "users": 40, "duration_seconds": 3},
                        {"name": "recovery", "users": 20, "duration_seconds": 2, "is_recovery": True},
                        {"name": "cooldown", "users": 0, "duration_seconds": 1, "is_cooldown": True},
                    ],
                    "think_seconds": [0.01, 0.02],
                    "assistant_read_seconds": [0.01, 0.02],
                    "ai_counts": [1, 2],
                    "ai_weights": [10, 10],
                    "timeout_seconds": 10,
                    "window_seconds": 10,
                    "window_min_requests": 5,
                    "stop_failure_rate_consecutive": 0.50,
                    "stop_consecutive_windows": 2,
                    "stop_failure_rate_immediate": 0.80,
                    "success_fraction": 0.999,
                    "ordinary_fast_fraction": 0.99,
                    "ordinary_ms": 400,
                    "ai_ms": 7000,
                    "voice_ms": 3000,
                    "minimum_samples_per_group": 5,
                    "seed": 20261103,
                }
                (run / "profile.json").write_text(json.dumps(profile), encoding="utf-8")
                (run / "manifest.json").write_text(
                    json.dumps({"profile": profile, "command_completed": True, "test_type": "stress"}),
                    encoding="utf-8"
                )
                (run / "pool.json").write_text(
                    json.dumps({
                        "user_ids": [f"mock_stress_{i}" for i in range(20000)],
                        "targets": [{"target_type": "learning_path", "target_id": "path1"}],
                        "audio_hosts": ["audio.example.invalid"],
                    }),
                    encoding="utf-8"
                )

                (run / "mock_stress_runner.py").write_text(
                    'import sys\n'
                    f'sys.path.insert(0, {repr(str(ROOT))})\n'
                    'import stress_locustfile as scenario\n'
                    'class AudioClient:\n'
                    '    def __enter__(self): return self\n'
                    '    def __exit__(self, *args): pass\n'
                    '    def get(self, *args, **kwargs):\n'
                    '        return type("Response", (), {"status_code": 200, "content": b"mp3", "headers": {"Content-Type": "audio/mpeg"}})()\n'
                    'scenario.requests.Session = AudioClient\n'
                    'from stress_locustfile import StressQuestionnaireUser, StressShape\n',
                    encoding="utf-8"
                )

                env = {
                    **os.environ,
                    "PERF_PROFILE": str(run / "profile.json"),
                    "PERF_DATA": str(run / "pool.json"),
                    "PERF_RUN_DIR": str(run),
                }

                result = subprocess.run(
                    [sys.executable, "-m", "locust", "-f", str(run / "mock_stress_runner.py"),
                     "--headless", "--host", f"http://127.0.0.1:{server.server_port}"],
                    env=env, capture_output=True, text=True, timeout=60
                )
                self.assertEqual(result.returncode, 0, result.stderr[-4000:])

                summary = analyze_stress.analyze(run)
                self.assertIn(summary["status"], ("PASS", "FAIL", "OBSERVED"))
                self.assertTrue((run / "report.html").exists())
                self.assertGreater(summary["total_requests"], 0)
        finally:
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    unittest.main()
