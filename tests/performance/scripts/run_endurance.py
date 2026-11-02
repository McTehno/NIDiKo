"""Pripravi zagon; omrežje uporabi šele z --execute."""
import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import ROOT, duration, load_profile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path, default=ROOT / "profiles/endurance.json")
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--base-url", default=os.getenv("PERF_BASE_URL"))
    parser.add_argument("--app-commit", required=True, help="Dejanski commit na stagingu")
    parser.add_argument("--environment-note", required=True, help="Infrastruktura, način zagona, baza, kvote")
    parser.add_argument("--output", type=Path, default=ROOT.parents[1] / "test-results/performance")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    profile = load_profile(args.profile)
    base = urlsplit(args.base_url or "")
    if base.scheme not in ("http", "https") or not base.hostname or base.username or base.password or base.query or base.fragment or base.path not in ("", "/"):
        parser.error("Podaj osnovni naslov brez /api, poverilnic ali parametrov.")
    data = json.loads(args.data.read_text(encoding="utf-8"))
    if not data.get("targets") or not data.get("audio_hosts") or len(set(data.get("user_ids", []))) != len(data.get("user_ids", [])) or len(data.get("user_ids", [])) < profile["users"]:
        parser.error("Neveljavni testni podatki ali premalo ločenih profilov.")
    # Deliberately no credentials or user IDs in public manifests.
    expected_ai = sum(n*w for n, w in zip(profile["ai_counts"], profile["ai_weights"])) / sum(profile["ai_weights"])
    print(json.dumps({"seconds_estimate": duration(profile), "users": profile["users"],
                      "available_journeys": len(data["user_ids"]),
                      "mean_ai_messages_per_ai_journey": expected_ai,
                      "max_ai_calls_for_pool": len(data["user_ids"]) * 20,
                      "execute": args.execute}, indent=2))
    if not args.execute:
        return 0
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run = args.output.resolve() / run_id
    run.mkdir(parents=True, exist_ok=False)
    (run / "profile.json").write_text(json.dumps(profile, indent=2), encoding="utf-8")
    try:
        test_commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
        dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip())
    except subprocess.CalledProcessError:
        test_commit, dirty = "unknown", True
    manifest = {"run_id": run_id, "app_commit": args.app_commit, "test_commit": test_commit,
                "test_worktree_dirty": dirty, "base_url": args.base_url,
                "environment_note": args.environment_note, "profile": profile,
                "targets": data["targets"], "user_pool_size": len(data["user_ids"]),
                "started_at": datetime.now(timezone.utc).isoformat(),
                "command_completed": False}
    (run / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    env = {**os.environ, "PERF_PROFILE": str(run / "profile.json"),
           "PERF_RUN_DIR": str(run), "PERF_DATA": str(args.data.resolve())}
    command = [sys.executable, "-m", "locust", "-f", str(ROOT / "locustfile.py"),
               "--headless", "--host", args.base_url.rstrip("/"),
               "--csv", str(run / "locust"), "--csv-full-history", "--html", str(run / "locust.html")]
    code = 2
    try:
        with (run / "run.log").open("w", encoding="utf-8") as log:
            try:
                code = subprocess.run(command, cwd=ROOT, env=env, stdout=log,
                                      stderr=subprocess.STDOUT,
                                      timeout=duration(profile) + 300).returncode
            except subprocess.TimeoutExpired:
                log.write("\nPresežen čas izvajanja; zagon je prekinjen.\n")
                code = 2
        manifest["command_completed"] = True
    finally:
        manifest.update(exit_code=code, ended_at=datetime.now(timezone.utc).isoformat())
        (run / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        analysis_code = subprocess.call([sys.executable, str(ROOT / "scripts/analyze_results.py"), str(run)]) if (run / "events.jsonl").exists() else 2
        print(f"Rezultati: {run}")
    return code or analysis_code


if __name__ == "__main__":
    raise SystemExit(main())
