"""Zagon večstopenjskega stresnega testa NIDiKo.

Brez stikala --execute izpiše načrt, oceno trajanja in oceno klicev AI.
Z --execute pripravi manifest in zažene test v ločenem podprocesu Locusta.
"""
import argparse
import json
import math
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

# Vključimo pot do skupnih modulov
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import ROOT, load_stress_profile, stress_duration


def calculate_estimates(profile, pool_size):
    """Izračun ocen trajanja, števila reševanj in obsega klicev AI."""
    total_seconds = stress_duration(profile)
    expected_ai_per_ai_journey = (
        sum(n * w for n, w in zip(profile["ai_counts"], profile["ai_weights"]))
        / sum(profile["ai_weights"])
    )

    # Ocena povprečnega trajanja enega reševanja vprašalnika (14 vprašanj)
    avg_think = sum(profile["think_seconds"]) / 2
    avg_ai_read = sum(profile["assistant_read_seconds"]) / 2
    avg_questions = 14
    base_journey_seconds = avg_questions * avg_think
    ai_extra_seconds = expected_ai_per_ai_journey * avg_ai_read
    # 40 % mest ima AI, 5 % glas
    avg_journey_duration = base_journey_seconds + 0.40 * ai_extra_seconds

    stage_estimates = []
    total_estimated_journeys = 0
    current_users = 0
    spawn_rate = profile["spawn_rate"]

    for stage in profile["stages"]:
        target_users = stage["users"]
        ramp_seconds = math.ceil(abs(target_users - current_users) / spawn_rate)
        steady_seconds = stage["duration_seconds"]

        # Ocena števila zaključenih potekov v tej stopnji
        effective_users = (current_users + target_users) / 2 if ramp_seconds > 0 else target_users
        est_ramp_journeys = (effective_users * ramp_seconds / avg_journey_duration) if ramp_seconds > 0 else 0
        est_steady_journeys = (target_users * steady_seconds / avg_journey_duration) if target_users > 0 else 0
        stage_journeys = round(est_ramp_journeys + est_steady_journeys)
        total_estimated_journeys += stage_journeys

        stage_estimates.append({
            "stage": stage["name"],
            "target_users": target_users,
            "ramp_seconds": ramp_seconds,
            "steady_seconds": steady_seconds,
            "stage_total_seconds": ramp_seconds + steady_seconds,
            "estimated_journeys": stage_journeys,
        })
        current_users = target_users

    estimated_ai_journeys = round(total_estimated_journeys * 0.40)
    estimated_ai_messages = round(estimated_ai_journeys * expected_ai_per_ai_journey)
    estimated_voice_calls = round(total_estimated_journeys * 0.05)

    return {
        "total_duration_seconds": total_seconds,
        "total_duration_minutes": round(total_seconds / 60, 1),
        "available_user_pool": pool_size,
        "estimated_total_journeys": total_estimated_journeys,
        "estimated_ai_journeys": estimated_ai_journeys,
        "mean_ai_messages_per_ai_journey": round(expected_ai_per_ai_journey, 2),
        "estimated_ai_assistant_messages": estimated_ai_messages,
        "estimated_voice_calls": estimated_voice_calls,
        "pool_sufficient": pool_size >= total_estimated_journeys * 1.5,
        "stages": stage_estimates,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path, default=ROOT / "profiles/stress.json",
                        help="Pot do konfiguracijske datoteke stresnega profila.")
    parser.add_argument("--data", type=Path, required=True,
                        help="Pot do evidence testnih podatkov (pool.json).")
    parser.add_argument("--base-url", default=os.getenv("PERF_BASE_URL"),
                        help="Osnovni naslov staginga (ali iz PERF_BASE_URL).")
    parser.add_argument("--app-commit", required=True,
                        help="Dejanski commit aplikacije nameščene na stagingu.")
    parser.add_argument("--environment-note", required=True,
                        help="Opis konfiguracije strežnika, baze, Dockerja in kvot.")
    parser.add_argument("--output", type=Path, default=ROOT.parents[1] / "test-results/performance/stress",
                        help="Izhodna mapa za rezultate stresnega testiranja.")
    parser.add_argument("--execute", action="store_true",
                        help="Zaženi dejanski test; brez tega stikala se izpiše le ocena načrta.")
    args = parser.parse_args()

    profile = load_stress_profile(args.profile)

    base = urlsplit(args.base_url or "")
    if (base.scheme not in ("http", "https") or not base.hostname or base.username or
            base.password or base.query or base.fragment or base.path not in ("", "/")):
        parser.error("Podaj veljaven osnovni naslov brez poti /api, poverilnic ali parametrov.")

    data = json.loads(args.data.read_text(encoding="utf-8"))
    pool_size = len(data.get("user_ids", []))
    max_planned_users = max(s["users"] for s in profile["stages"])
    if (not data.get("targets") or not data.get("audio_hosts") or
            len(set(data.get("user_ids", []))) != pool_size or pool_size < max_planned_users):
        parser.error("Neveljavni testni podatki ali premalo ločenih profilov za največjo načrtovano stopnjo.")

    estimates = calculate_estimates(profile, pool_size)

    # Izpis načrta in ocene klicev pred izvedbo
    print(json.dumps({
        "mode": "EXECUTE" if args.execute else "PLAN_PREVIEW",
        "app_commit": args.app_commit,
        "base_url": args.base_url,
        "max_concurrent_users": max_planned_users,
        "estimates": estimates,
    }, indent=2, ensure_ascii=False))

    if not args.execute:
        print("\n[INFO] Za dejansko izvedbo dodaj stikalo --execute po potrditvi termina.")
        return 0

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run = args.output.resolve() / run_id
    run.mkdir(parents=True, exist_ok=False)

    (run / "profile.json").write_text(json.dumps(profile, indent=2, ensure_ascii=False), encoding="utf-8")

    try:
        test_commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
        dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip())
    except subprocess.CalledProcessError:
        test_commit, dirty = "unknown", True

    manifest = {
        "run_id": run_id,
        "test_type": "stress",
        "app_commit": args.app_commit,
        "test_commit": test_commit,
        "test_worktree_dirty": dirty,
        "base_url": args.base_url,
        "environment_note": args.environment_note,
        "profile": profile,
        "targets": data["targets"],
        "user_pool_size": pool_size,
        "estimates": estimates,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "command_completed": False,
    }
    (run / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    env = {
        **os.environ,
        "PERF_PROFILE": str(run / "profile.json"),
        "PERF_RUN_DIR": str(run),
        "PERF_DATA": str(args.data.resolve()),
    }

    command = [
        sys.executable, "-m", "locust", "-f", str(ROOT / "stress_locustfile.py"),
        "--headless", "--host", args.base_url.rstrip("/"),
        "--csv", str(run / "locust"), "--csv-full-history",
        "--html", str(run / "locust.html"),
    ]

    code = 2
    timeout_limit = estimates["total_duration_seconds"] + 600
    try:
        with (run / "run.log").open("w", encoding="utf-8") as log:
            try:
                code = subprocess.run(
                    command, cwd=ROOT, env=env, stdout=log,
                    stderr=subprocess.STDOUT, timeout=timeout_limit
                ).returncode
            except subprocess.TimeoutExpired:
                log.write("\nPresežen varnostni čas izvajanja; zagon je bil prekinjen.\n")
                code = 2
        manifest["command_completed"] = True
    finally:
        manifest.update(exit_code=code, ended_at=datetime.now(timezone.utc).isoformat())
        (run / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

        # Avtomatska analiza rezultatov stresnega testa
        analysis_code = 2
        if (run / "events.jsonl").exists():
            analysis_code = subprocess.call([
                sys.executable, str(ROOT / "scripts/analyze_stress.py"), str(run)
            ])
        print(f"\nRezultati stresnega testa: {run}")

    return code or analysis_code


if __name__ == "__main__":
    raise SystemExit(main())
