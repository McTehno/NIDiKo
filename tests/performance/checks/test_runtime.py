"""Kratek integracijski preizkus Locusta proti lokalnemu nadomestnemu API-ju."""
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
        self.send_json({"target_type": "learning_path", "target_id": "path1",
                        "questions": [{"id": "q1", "question": "Ali znate uporabiti splet?", "type": "yes_no"}]})

    def do_POST(self):
        data = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        if self.path.endswith("evaluate"):
            self.send_json({"user_id": data["user_id"], "target_id": data["target_id"],
                            "target_type": data["target_type"], "learning_unit_results": []})
        elif self.path.endswith("message"):
            self.send_json({"session_id": "mock-session", "answer": "Primer razlage."})
        else:
            self.send_json({"cached": True, "help_text": "Pomoč", "audio_url": "https://audio.example.invalid/file?sig=SECRET"})


@unittest.skipUnless(importlib.util.find_spec("locust"), "Locust ni nameščen")
class RuntimeCheck(unittest.TestCase):
    def test_real_locust_with_mock_services(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), MockAPI)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            with tempfile.TemporaryDirectory() as directory:
                run = Path(directory)
                profile = json.loads((ROOT / "profiles/endurance.json").read_text(encoding="utf-8"))
                profile.update(users=20, spawn_rate=100, warmup_seconds=1, steady_seconds=6,
                               recovery_seconds=2, think_seconds=[.02, .03], assistant_read_seconds=[.02, .03])
                (run / "profile.json").write_text(json.dumps(profile), encoding="utf-8")
                (run / "manifest.json").write_text(json.dumps({"profile": profile, "command_completed": True}), encoding="utf-8")
                (run / "pool.json").write_text(json.dumps({"user_ids": [f"mock{i}" for i in range(10000)],
                    "targets": [{"target_type": "learning_path", "target_id": "path1"}],
                    "audio_hosts": ["audio.example.invalid"]}), encoding="utf-8")
                # Stub only the external audio client; HTTP API calls use actual local sockets.
                (run / "mock_locust.py").write_text(
                    'import sys\nsys.path.insert(0, '+repr(str(ROOT))+')\n'
                    'import locustfile as scenario\n'
                    'class AudioClient:\n'
                    '    def __enter__(self): return self\n'
                    '    def __exit__(self, *args): pass\n'
                    '    def get(self, *args, **kwargs):\n'
                    '        return type("Response", (), {"status_code": 200, "content": b"mp3", "headers": {"Content-Type": "audio/mpeg"}})()\n'
                    'scenario.requests.Session = AudioClient\n'
                    'from locustfile import QuestionnaireUser, EnduranceShape\n', encoding="utf-8")
                env = {**os.environ, "PERF_PROFILE": str(run / "profile.json"),
                       "PERF_DATA": str(run / "pool.json"), "PERF_RUN_DIR": str(run)}
                result = subprocess.run([sys.executable, "-m", "locust", "-f", str(run / "mock_locust.py"),
                    "--headless", "--host", f"http://127.0.0.1:{server.server_port}"],
                    env=env, capture_output=True, text=True, timeout=35)
                self.assertEqual(result.returncode, 0, result.stderr[-4000:])
                spec = importlib.util.spec_from_file_location("runtime_analysis", ROOT / "scripts/analyze_results.py")
                analyzer = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(analyzer)
                summary = analyzer.analyze(run)
                self.assertEqual(summary["status"], "PASS", summary)
                self.assertNotIn("SECRET", (run / "events.jsonl").read_text())
                self.assertGreater(summary["groups"]["ordinary/evaluate"]["count"], 0)
        finally:
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    unittest.main()
