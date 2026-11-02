"""Preverjanje napak v ocenjevanju; brez povezave s stagingom."""
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from common import answer_payload, duration, load_profile

spec = importlib.util.spec_from_file_location("analysis", ROOT / "scripts/analyze_results.py")
analysis = importlib.util.module_from_spec(spec)
spec.loader.exec_module(analysis)


class AnalysisChecks(unittest.TestCase):
    def setUp(self):
        self.profile = load_profile(ROOT / "profiles/endurance.json")

    def test_exact_threshold_and_failure_denominator(self):
        samples = [{"group": "ordinary/evaluate", "ms": 400, "ok": True}] * 999
        samples.append({"group": "ordinary/evaluate", "ms": 1, "ok": False})
        self.assertEqual(analysis.summarize(samples, self.profile)["status"], "PASS")
        samples.append({"group": "ordinary/evaluate", "ms": 1, "ok": False})
        self.assertEqual(analysis.summarize(samples, self.profile)["status"], "FAIL")

    def test_one_slow_ai_fails(self):
        self.assertEqual(analysis.summarize([{"group": "ai", "ms": 7001, "ok": True}], self.profile)["status"], "FAIL")

    def test_cold_voice_has_no_latency_verdict(self):
        self.assertEqual(analysis.summarize([{"group": "voice_cold", "ms": 20000, "ok": True}], self.profile)["status"], "OBSERVED")

    def test_answer_mapping(self):
        answer = answer_payload({"id": "q1", "question": "Primer?", "related_topic_id": "t1", "related_competency_codes": ["1.1"]})
        self.assertEqual(answer["topic_id"], "t1")
        self.assertEqual(answer["competency_codes"], ["1.1"])

    def test_profile_and_duration(self):
        self.assertEqual(duration(self.profile), 29320)

    def fixture(self, run, stopped=True, fatal=False):
        self.profile["steady_seconds"] = 10
        self.profile["recovery_seconds"] = 2
        start = 100
        end = start + self.profile["steady_seconds"]
        (run / "manifest.json").write_text(json.dumps({"profile": self.profile, "command_completed": True}), encoding="utf-8")
        rows = [{"kind": "schedule", "time": 1, "steady_start": start, "steady_end": end},
                {"kind": "population", "time": start, "phase": "steady", "users": 100}]
        rows.extend({"kind": "population", "time": stamp, "phase": "steady", "users": 100} for stamp in range(start+1, end))
        for group in ("ordinary/questionnaire", "ordinary/evaluate", "ai", "voice_api", "voice_audio"):
            rows.append({"kind": "request", "time": start + 1, "phase": "steady", "group": group, "ms": 100, "ok": True, "cached": True})
        if stopped:
            rows.append({"kind": "stop", "time": end + self.profile["recovery_seconds"]})
        if fatal:
            rows.append({"kind": "fatal", "time": start + 2, "reason": "Zmanjkalo profilov"})
        (run / "events.jsonl").write_text(''.join(json.dumps(r)+'\n' for r in rows), encoding="utf-8")

    def test_complete_run(self):
        with tempfile.TemporaryDirectory() as directory:
            run = Path(directory)
            self.fixture(run)
            result = analysis.analyze(run)
            self.assertEqual(result["status"], "PASS")
            self.assertTrue(result["groups"]["ai"]["small_sample"])
            self.assertTrue((run / "report.html").exists())

    def test_interrupted_run_is_invalid(self):
        with tempfile.TemporaryDirectory() as directory:
            run = Path(directory)
            self.fixture(run, stopped=False)
            self.assertEqual(analysis.analyze(run)["status"], "INVALID")

    def test_exhausted_pool_is_invalid(self):
        with tempfile.TemporaryDirectory() as directory:
            run = Path(directory)
            self.fixture(run, fatal=True)
            self.assertEqual(analysis.analyze(run)["status"], "INVALID")


if __name__ == "__main__":
    unittest.main()
