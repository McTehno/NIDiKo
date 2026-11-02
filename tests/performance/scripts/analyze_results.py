"""Analiza točnih vzorcev, brez približkov percentilov iz Locusta."""
import argparse
import html
import json
import math
from collections import defaultdict
from pathlib import Path


def summarize(samples, profile):
    if not samples:
        return {"count": 0, "status": "NO_DATA"}
    successful = [row for row in samples if row["ok"]]
    times = sorted(row["ms"] for row in samples)
    group = samples[0]["group"]
    threshold = (profile["ordinary_ms"] if group.startswith("ordinary/") else
                 profile["ai_ms"] if group == "ai" else profile["voice_ms"])
    fast = sum(row["ok"] and row["ms"] <= threshold for row in samples) / len(samples)
    success = len(successful) / len(samples)
    required_fast = profile["ordinary_fast_fraction"] if group.startswith("ordinary/") else 1
    passed = success >= profile["success_fraction"] and fast >= required_fast
    # First creation is measured but has no agreed latency criterion.
    exploratory = group == "voice_cold"
    return {"count": len(samples), "success_fraction": success,
            "fast_fraction": fast, "threshold_ms": threshold,
            "p99_ms": times[max(0, math.ceil(len(times)*.99)-1)], "max_ms": times[-1],
            "small_sample": len(samples) < profile["minimum_samples_per_group"],
            "status": ("FAIL" if success < profile["success_fraction"] else "OBSERVED") if exploratory else "PASS" if passed else "FAIL"}


def analyze(run):
    manifest = json.loads((run / "manifest.json").read_text(encoding="utf-8"))
    profile = manifest["profile"]
    groups, windows = defaultdict(list), defaultdict(lambda: defaultdict(list))
    schedule, stopped, fatal = None, None, []
    populations, journeys = [], {"started": 0, "completed": 0, "failed": 0}
    truncated = False
    with (run / "events.jsonl").open(encoding="utf-8") as stream:
        for line in stream:
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                truncated = True
                continue
            kind = row["kind"]
            if kind == "schedule":
                schedule = row
            elif kind == "stop":
                stopped = row
            elif kind == "fatal":
                fatal.append(row["reason"])
            elif kind == "population" and row["phase"] == "steady":
                populations.append(row)
            elif kind == "journey_start":
                journeys["started"] += 1
            elif kind == "journey_end":
                journeys["completed" if row["ok"] else "failed"] += 1
            elif kind == "request" and row["phase"] == "steady":
                group = row["group"]
                if group == "voice_api":
                    group = "voice_cached" if row.get("cached") is True else "voice_cold" if row.get("cached") is False else "voice_error"
                row["group"] = group
                groups[group].append(row)
                if schedule:
                    index = int((row["time"] - schedule["steady_start"]) // profile["window_seconds"])
                    windows[index][group].append(row)
    full_duration = bool(schedule and stopped and stopped["time"] >= schedule["steady_end"] + profile["recovery_seconds"] - 2)
    population_ok = bool(schedule and populations) and all(p["users"] == profile["users"] for p in populations)
    if population_ok:
        stamps = [p["time"] for p in populations]
        population_ok = (stamps[0] <= schedule["steady_start"] + 3
                         and stamps[-1] >= schedule["steady_end"] - 3
                         and all(b-a <= 3 for a, b in zip(stamps, stamps[1:])))
    results = {name: summarize(rows, profile) for name, rows in groups.items()}
    required = {"ordinary/questionnaire", "ordinary/evaluate", "ai", "voice_cached", "voice_audio"}
    missing = sorted(required - results.keys())
    valid = full_duration and population_ok and not fatal and not truncated and manifest.get("command_completed", False)
    status = ("INVALID" if not valid else "FAIL" if any(v["status"] == "FAIL" for v in results.values())
              else "INCOMPLETE" if missing else "PASS")
    summary = {"status": status, "full_duration": full_duration, "population_ok": population_ok,
               "missing_groups": missing, "fatal": fatal, "truncated_events": truncated,
               "groups": results, "journeys_all_phases": journeys,
               "windows": {str(i): {g: summarize(v, profile) for g, v in gs.items()}
                           for i, gs in sorted(windows.items())},
               "note": "PASS opisuje opažene vzorce; ni dokaz dolgoročne 99,9 % zanesljivosti. Glasovni API in prenos zvoka sta ločeni meritvi, brez meritve začetka predvajanja. Infrastruktura zahteva ločeno presojo."}
    (run / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    rows = "".join(f"<tr><td>{html.escape(name)}</td><td>{v['count']}</td><td>{v.get('p99_ms', 0):.1f}</td><td>{v.get('max_ms', 0):.1f}</td><td>{v['status']}</td></tr>" for name, v in results.items())
    # Standalone SVG graph of p99 over time, ordinary and AI separately scaled.
    graphs = []
    for name in sorted(results):
        points = [(int(i), values[name]["p99_ms"]) for i, values in summary["windows"].items() if name in values]
        if points:
            xmax, ymax = max(x for x, y in points) or 1, max(y for x, y in points) or 1
            coordinates = " ".join(f"{40+x/xmax*700:.1f},{170-y/ymax*130:.1f}" for x, y in points)
            graphs.append(f'<h3>{html.escape(name)} — p99</h3><svg viewBox="0 0 800 210" role="img" aria-label="p99 po intervalih"><path d="M40 20V170H750" fill="none" stroke="black"/><polyline points="{coordinates}" fill="none" stroke="steelblue" stroke-width="2"/><text x="40" y="200">Intervali po {profile["window_seconds"]} s; vrh osi {ymax:.1f} ms</text></svg>')
    (run / "report.html").write_text('<!doctype html><html lang="sl"><meta charset="utf-8"><title>Vzdržljivostni test</title><style>body{font:16px system-ui;max-width:1000px;margin:40px auto}td,th{padding:8px;border:1px solid #ccc}table{border-collapse:collapse}svg{width:100%}</style>'
        + f'<h1>Rezultat: {status}</h1><p>{html.escape(summary["note"])}</p><table><tr><th>Skupina</th><th>Vzorcev</th><th>p99 ms</th><th>Največ ms</th><th>Ocena</th></tr>{rows}</table>'
        + ''.join(graphs) + '<h2>Podrobnosti</h2><pre>' + html.escape(json.dumps(summary, indent=2, ensure_ascii=False)) + '</pre></html>', encoding="utf-8")
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    result = analyze(parser.parse_args().run)
    print(result["status"])
    raise SystemExit(0 if result["status"] == "PASS" else 1)
