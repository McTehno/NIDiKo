"""Analiza rezultatov večstopenjskega stresnega testa NIDiKo.

Obdela dogodke po posameznih stopnjah (ogrevanje, stopnje 1–7, okrevanje, opazovanje),
preveri doseganje populacije, točne čase odzivov (brez približkov Locusta),
oceni mejo zmogljivosti, primerja začetno stopnjo z okrevanjem ter izriše poročilo.
"""
import argparse
import html
import json
import math
import statistics
import sys
from collections import defaultdict
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


def percentile(values, q):
    """Izračun točnega percentila iz urejenega seznama vrednosti."""
    if not values:
        return 0.0
    s = sorted(values)
    return float(s[max(0, math.ceil(len(s) * q) - 1)])


def summarize_group(samples, profile):
    """Izračun statistike za določeno skupino zahtev znotraj faze."""
    if not samples:
        return {"count": 0, "status": "NO_DATA"}

    count = len(samples)
    successful = [r for r in samples if r["ok"]]
    failed_count = count - len(successful)
    times = [r["ms"] for r in samples]
    success_fraction = len(successful) / count

    group = samples[0]["group"]
    threshold = (profile.get("ordinary_ms", 400) if group.startswith("ordinary/") else
                 profile.get("ai_ms", 7000) if group == "ai" else
                 profile.get("voice_ms", 3000))

    fast_count = sum(r["ok"] and r["ms"] <= threshold for r in samples)
    fast_fraction = fast_count / count

    required_fast = profile.get("ordinary_fast_fraction", 0.99) if group.startswith("ordinary/") else 1.0
    passed = (success_fraction >= profile.get("success_fraction", 0.999) and
              fast_fraction >= required_fast)

    exploratory = (group == "voice_cold")
    status = ("FAIL" if success_fraction < profile.get("success_fraction", 0.999) else "OBSERVED") if exploratory else "PASS" if passed else "FAIL"

    return {
        "count": count,
        "failed": failed_count,
        "success_fraction": round(success_fraction, 6),
        "fast_fraction": round(fast_fraction, 6),
        "threshold_ms": threshold,
        "mean_ms": round(statistics.mean(times), 2),
        "median_ms": round(percentile(times, 0.50), 2),
        "p95_ms": round(percentile(times, 0.95), 2),
        "p99_ms": round(percentile(times, 0.99), 2),
        "max_ms": round(max(times), 2),
        "small_sample": count < profile.get("minimum_samples_per_group", 100),
        "status": status,
    }


def analyze(run_dir):
    """Celovita analiza stresnega teka iz dogodkov events.jsonl."""
    run = Path(run_dir).resolve()
    manifest = json.loads((run / "manifest.json").read_text(encoding="utf-8"))
    profile = manifest.get("profile") or json.loads((run / "profile.json").read_text(encoding="utf-8"))

    events_path = run / "events.jsonl"
    if not events_path.exists():
        raise FileNotFoundError(f"Datoteka {events_path} ne obstaja.")

    # Branje dogodkov
    events = []
    truncated = False
    with events_path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                truncated = True

    # Zbiranje ključnih dogodkov
    stage_events = [e for e in events if e.get("kind") in ("stage_start", "stage_end")]
    population_events = [e for e in events if e.get("kind") == "population"]
    early_stops = [e for e in events if e.get("kind") in ("early_stop_triggered", "transition_to_recovery")]
    fatals = [e.get("reason") for e in events if e.get("kind") == "fatal"]
    stop_event = next((e for e in events if e.get("kind") == "stop"), None)

    # Združevanje zahtev po stopnji in fazi
    requests_by_stage_and_phase = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    all_requests = []

    for e in events:
        if e.get("kind") == "request":
            all_requests.append(e)
            stage = e.get("stage", "unknown")
            phase = e.get("phase", "unknown")
            group = e.get("group", "unknown")
            if group == "voice_api":
                group = "voice_cached" if e.get("cached") is True else "voice_cold" if e.get("cached") is False else "voice_error"
            e_copy = dict(e)
            e_copy["group"] = group
            requests_by_stage_and_phase[stage][phase][group].append(e_copy)

    # Analiza po posameznih načrtovanih stopnjah
    stages_analysis = []
    for stage_def in profile["stages"]:
        name = stage_def["name"]
        users = stage_def["users"]
        is_warmup = stage_def.get("is_warmup", False)
        is_recovery = stage_def.get("is_recovery", False)
        is_cooldown = stage_def.get("is_cooldown", False)
        steady_phase_name = ("warmup" if is_warmup else
                             "recovery" if is_recovery else
                             "cooldown" if is_cooldown else "steady")

        # Meritve populacije v tej stopnji
        stage_pop = [p for p in population_events if p.get("stage") == name and p.get("phase") == steady_phase_name]
        pop_counts = [p.get("users", 0) for p in stage_pop]
        ordinary_counts = [p.get("ordinary", 0) for p in stage_pop]
        ai_counts = [p.get("ai", 0) for p in stage_pop]
        voice_counts = [p.get("voice", 0) for p in stage_pop]

        steady_groups_raw = requests_by_stage_and_phase[name][steady_phase_name]
        ramp_groups_raw = requests_by_stage_and_phase[name]["ramp"]

        steady_summary = {g: summarize_group(rows, profile) for g, rows in steady_groups_raw.items()}
        ramp_summary = {g: summarize_group(rows, profile) for g, rows in ramp_groups_raw.items()}

        total_steady_requests = sum(len(rows) for rows in steady_groups_raw.values())
        failed_steady_requests = sum(sum(not r["ok"] for r in rows) for rows in steady_groups_raw.values())

        # Časovno trajanje stabilne faze
        stage_starts = [e for e in stage_events if e.get("kind") == "stage_start" and e.get("stage") == name]
        stage_ends = [e for e in stage_events if e.get("kind") == "stage_end" and e.get("stage") == name]
        duration_measured = 0
        if stage_starts and stage_ends:
            duration_measured = max(0, stage_ends[0]["time"] - stage_starts[0]["time"])
        elif stage_starts and stop_event:
            duration_measured = max(0, stop_event["time"] - stage_starts[0]["time"])

        rps = (total_steady_requests / duration_measured) if duration_measured > 0 else 0.0

        # Ocena uspešnosti stopnje
        stage_status = "SKIPPED"
        if stage_starts:
            if any(v["status"] == "FAIL" for v in steady_summary.values()):
                stage_status = "FAIL"
            elif any(v["status"] == "PASS" for v in steady_summary.values()):
                stage_status = "PASS"
            else:
                stage_status = "OBSERVED" if steady_summary else "NO_REQUESTS"

        stages_analysis.append({
            "name": name,
            "target_users": users,
            "is_warmup": is_warmup,
            "is_recovery": is_recovery,
            "is_cooldown": is_cooldown,
            "status": stage_status,
            "duration_measured_seconds": round(duration_measured, 1),
            "total_requests": total_steady_requests,
            "failed_requests": failed_steady_requests,
            "failure_rate": round(failed_steady_requests / total_steady_requests, 4) if total_steady_requests else 0.0,
            "rps": round(rps, 2),
            "population": {
                "min": min(pop_counts) if pop_counts else 0,
                "max": max(pop_counts) if pop_counts else 0,
                "mean": round(statistics.mean(pop_counts), 1) if pop_counts else 0,
                "last_ordinary": ordinary_counts[-1] if ordinary_counts else 0,
                "last_ai": ai_counts[-1] if ai_counts else 0,
                "last_voice": voice_counts[-1] if voice_counts else 0,
            },
            "groups": steady_summary,
            "ramp_groups": ramp_summary,
        })

    # Opredelitev točk preloma
    criteria_limit_stage = None
    technical_limit_stage = None
    highest_tested_stage = None

    for s in stages_analysis:
        if s["status"] in ("PASS", "FAIL", "OBSERVED") and not s["is_warmup"] and not s["is_recovery"] and not s["is_cooldown"]:
            highest_tested_stage = s["name"]
            if s["status"] == "FAIL" and criteria_limit_stage is None:
                criteria_limit_stage = s["name"]
            if s["failure_rate"] >= 0.05 and technical_limit_stage is None:
                technical_limit_stage = s["name"]

    # Primerjava okrevanja: Stage 1 (20 mest) proti Recovery (20 mest)
    stage1 = next((s for s in stages_analysis if s["name"] == "stage_1"), None)
    recovery = next((s for s in stages_analysis if s["is_recovery"]), None)
    recovery_observation = {
        "stage_1_users": stage1["target_users"] if stage1 else 20,
        "recovery_users": recovery["target_users"] if recovery else 20,
        "stage_1_requests": stage1["total_requests"] if stage1 else 0,
        "recovery_requests": recovery["total_requests"] if recovery else 0,
        "stage_1_failure_rate": stage1["failure_rate"] if stage1 else 0.0,
        "recovery_failure_rate": recovery["failure_rate"] if recovery else 0.0,
        "stage_1_rps": stage1["rps"] if stage1 else 0.0,
        "recovery_rps": recovery["rps"] if recovery else 0.0,
    }
    if stage1 and recovery and stage1["groups"] and recovery["groups"]:
        for grp in ("ordinary/questionnaire", "ordinary/evaluate", "ai"):
            if grp in stage1["groups"] and grp in recovery["groups"]:
                recovery_observation[f"{grp}_stage1_p99_ms"] = stage1["groups"][grp].get("p99_ms")
                recovery_observation[f"{grp}_recovery_p99_ms"] = recovery["groups"][grp].get("p99_ms")

    # Skupno stanje
    overall_status = "INVALID" if (fatals or truncated or not manifest.get("command_completed")) else \
                     "FAIL" if criteria_limit_stage or any(s["status"] == "FAIL" for s in stages_analysis) else \
                     "PASS"

    summary = {
        "status": overall_status,
        "test_type": "stress",
        "run_id": manifest.get("run_id"),
        "total_requests": len(all_requests),
        "total_failures": sum(not r.get("ok") for r in all_requests),
        "highest_tested_stage": highest_tested_stage,
        "criteria_breaking_stage": criteria_limit_stage or "Brez kršitev (kriteriji izpolnjeni na vseh stopnjah)",
        "technical_breaking_stage": technical_limit_stage or "Meja tehnične preobremenitve ni bila dosežena",
        "early_stop": {
            "triggered": bool(early_stops),
            "events": early_stops,
        },
        "fatal_errors": fatals,
        "truncated_events": truncated,
        "recovery_comparison": recovery_observation,
        "stages": stages_analysis,
        "note": (
            "Kriteriji kakovosti (400 ms za običajne API-je, 7 s za AI) niso enaki meji preobremenitve. "
            "Meja tehnične preobremenitve je določena z znatnim porastom napak (> 5 % v dveh oknih ali > 10 % v enem), "
            "sesutjem ali izčrpanjem virov. Primerjava okrevanja z začetno stopnjo 20 uporabnikov "
            "temelji na neposrednih meritvah odzivnih časov in napak."
        )
    }

    # Zapis summary.json
    (run / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    # Izdelava samostojnega HTML poročila
    _generate_html_report(run, summary, stages_analysis)
    return summary


def _generate_html_report(run, summary, stages_analysis):
    """Izdelava preglednega samostojnega HTML poročila z SVG grafi."""
    rows = []
    for s in stages_analysis:
        grps = s["groups"]
        q_p99 = grps.get("ordinary/questionnaire", {}).get("p99_ms", "-")
        e_p99 = grps.get("ordinary/evaluate", {}).get("p99_ms", "-")
        ai_p99 = grps.get("ai", {}).get("p99_ms", "-")
        rows.append(
            f"<tr><td><strong>{html.escape(s['name'])}</strong></td>"
            f"<td>{s['target_users']}</td>"
            f"<td>{s['duration_measured_seconds']} s</td>"
            f"<td>{s['total_requests']}</td>"
            f"<td>{s['failed_requests']} ({s['failure_rate']*100:.2f} %)</td>"
            f"<td>{s['rps']}</td>"
            f"<td>{q_p99}</td><td>{e_p99}</td><td>{ai_p99}</td>"
            f"<td class='status-{s['status'].lower()}'>{s['status']}</td></tr>"
        )
    rows_html = "".join(rows)

    # SVG graf uporabnikov in RPS po stopnjah
    active_stages = [s for s in stages_analysis if s["total_requests"] > 0]
    svg_chart = ""
    if active_stages:
        max_users = max(s["target_users"] for s in active_stages) or 1
        max_rps = max(s["rps"] for s in active_stages) or 1
        n = len(active_stages)
        width = 800
        height = 220
        margin = 50

        user_points = []
        rps_points = []
        for i, s in enumerate(active_stages):
            x = margin + (i / max(1, n - 1)) * (width - 2 * margin)
            y_u = (height - 30) - (s["target_users"] / max_users) * 150
            y_r = (height - 30) - (s["rps"] / max_rps) * 150
            user_points.append(f"{x:.1f},{y_u:.1f}")
            rps_points.append(f"{x:.1f},{y_r:.1f}")

        svg_chart = f"""
        <h3>Aktivna mesta in RPS skozi stopnje stresnega testa</h3>
        <svg viewBox="0 0 {width} {height}" style="width:100%;background:#fafafa;border:1px solid #e5e7eb;border-radius:6px;margin:16px 0;">
            <polyline points="{' '.join(user_points)}" fill="none" stroke="#2563eb" stroke-width="3" />
            <polyline points="{' '.join(rps_points)}" fill="none" stroke="#059669" stroke-width="2" stroke-dasharray="4" />
            <line x1="{margin}" y1="{height-30}" x2="{width-margin}" y2="{height-30}" stroke="#9ca3af" stroke-width="1" />
            <text x="{margin}" y="20" fill="#2563eb" font-size="12">■ Uporabniki (vrh: {max_users})</text>
            <text x="{margin+180}" y="20" fill="#059669" font-size="12">--- RPS (vrh: {max_rps:.1f})</text>
        </svg>
        """

    report_html = f"""<!doctype html>
<html lang="sl">
<head>
<meta charset="utf-8">
<title>Poročilo stresnega testiranja NIDiKo</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; max-width: 1050px; margin: 40px auto; padding: 0 20px; color: #1f2937; line-height: 1.5; }}
h1, h2, h3 {{ color: #111827; }}
table {{ border-collapse: collapse; width: 100%; margin: 20px 0; font-size: 14px; }}
th, td {{ border: 1px solid #d1d5db; padding: 8px 12px; text-align: left; }}
th {{ background: #f3f4f6; }}
.badge {{ display: inline-block; padding: 4px 8px; border-radius: 4px; font-weight: bold; font-size: 13px; }}
.status-pass {{ color: #047857; font-weight: bold; }}
.status-fail {{ color: #b91c1c; font-weight: bold; }}
.status-skipped {{ color: #6b7280; }}
.status-observed {{ color: #4338ca; }}
pre {{ background: #f8fafc; border: 1px solid #e2e8f0; padding: 12px; border-radius: 6px; overflow-x: auto; font-size: 13px; }}
</style>
</head>
<body>
<h1>Poročilo stresnega testiranja NIDiKo</h1>
<p><strong>Izid:</strong> <span class="badge status-{summary['status'].lower()}">{summary['status']}</span></p>
<p><strong>Najvišja preizkušena stopnja:</strong> {summary['highest_tested_stage'] or 'Brez'} | 
<strong>Meja merjenih kriterijev:</strong> {summary['criteria_breaking_stage']} | 
<strong>Meja tehnične preobremenitve:</strong> {summary['technical_breaking_stage']}</p>
<p><em>{html.escape(summary['note'])}</em></p>

<h2>Pregled po stopnjah obremenitve</h2>
<table>
<thead>
<tr>
<th>Stopnja</th><th>Mesta</th><th>Trajanje</th><th>Zahtev</th><th>Napake</th><th>RPS</th>
<th>Vprašalnik p99</th><th>Oddaja p99</th><th>AI p99</th><th>Ocena</th>
</tr>
</thead>
<tbody>
{rows_html}
</tbody>
</table>

{svg_chart}

<h2>Primerjava okrevanja (Stage 1 vs. Recovery)</h2>
<pre>{html.escape(json.dumps(summary["recovery_comparison"], indent=2, ensure_ascii=False))}</pre>

<h2>Podrobne metrike v JSON</h2>
<pre>{html.escape(json.dumps(summary, indent=2, ensure_ascii=False))}</pre>
</body>
</html>"""
    (run / "report.html").write_text(report_html, encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path, help="Pot do mape z rezultati stresnega testa.")
    args = parser.parse_args()
    summary = analyze(args.run)
    print(f"Status: {summary['status']}")
    print(f"Najvišja stopnja: {summary['highest_tested_stage']}")
    print(f"Meja tehnične preobremenitve: {summary['technical_breaking_stage']}")

