"""Skupna konfiguracija brez odvisnosti od aplikacije."""
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def load_profile(path):
    profile = json.loads(Path(path).read_text(encoding="utf-8"))
    for key in ("users", "spawn_rate", "warmup_seconds", "steady_seconds",
                "recovery_seconds", "window_seconds", "timeout_seconds"):
        if not isinstance(profile[key], (int, float)) or profile[key] <= 0:
            raise ValueError(f"Neveljavna nastavitev: {key}")
    if int(profile["users"]) != profile["users"] or profile["users"] % 20:
        raise ValueError("Število uporabnikov mora biti večkratnik 20 (deleža 40 % in 5 %).")
    for key in ("think_seconds", "assistant_read_seconds"):
        low, high = profile[key]
        if low < 0 or high < low:
            raise ValueError(f"Neveljaven interval: {key}")
    if not (len(profile["ai_counts"]) == len(profile["ai_weights"]) > 0):
        raise ValueError("Neveljavna porazdelitev AI sporočil.")
    if any(not isinstance(n, int) or not 1 <= n <= 20 for n in profile["ai_counts"]):
        raise ValueError("Dovoljenih je 1–20 sporočil.")
    if any(w <= 0 for w in profile["ai_weights"]):
        raise ValueError("Uteži morajo biti pozitivne.")
    return profile


def duration(profile):
    return (math.ceil(profile["users"] / profile["spawn_rate"])
            + profile["warmup_seconds"] + profile["steady_seconds"]
            + profile["recovery_seconds"])


def load_stress_profile(path):
    profile = json.loads(Path(path).read_text(encoding="utf-8"))
    for key in ("spawn_rate", "timeout_seconds", "window_seconds", "window_min_requests",
                "stop_failure_rate_consecutive", "stop_consecutive_windows",
                "stop_failure_rate_immediate"):
        if key not in profile:
            raise ValueError(f"Manjka obvezna nastavitev stresnega profila: {key}")
        if not isinstance(profile[key], (int, float)) or profile[key] <= 0:
            raise ValueError(f"Neveljavna vrednost: {key}")

    if "stages" not in profile or not isinstance(profile["stages"], list) or not profile["stages"]:
        raise ValueError("Stresni profil mora vsebovati vsaj eno stopnjo (stages).")

    for i, stage in enumerate(profile["stages"]):
        for stage_key in ("name", "users", "duration_seconds"):
            if stage_key not in stage:
                raise ValueError(f"Stopnja {i} nima nastavitve: {stage_key}")
        users = stage["users"]
        if not isinstance(users, int) or users < 0 or (users > 0 and users % 20 != 0):
            raise ValueError(f"Stopnja '{stage['name']}': število uporabnikov ({users}) mora biti 0 ali večkratnik 20.")
        if not isinstance(stage["duration_seconds"], (int, float)) or stage["duration_seconds"] <= 0:
            raise ValueError(f"Stopnja '{stage['name']}': neveljavno trajanje {stage['duration_seconds']}.")

    for key in ("think_seconds", "assistant_read_seconds"):
        low, high = profile[key]
        if low < 0 or high < low:
            raise ValueError(f"Neveljaven interval: {key}")
    if not (len(profile["ai_counts"]) == len(profile["ai_weights"]) > 0):
        raise ValueError("Neveljavna porazdelitev AI sporočil.")
    if any(not isinstance(n, int) or not 1 <= n <= 20 for n in profile["ai_counts"]):
        raise ValueError("Dovoljenih je 1–20 sporočil.")
    if any(w <= 0 for w in profile["ai_weights"]):
        raise ValueError("Uteži morajo biti pozitivne.")
    return profile


def stress_duration(profile):
    total = 0
    current_users = 0
    spawn_rate = profile["spawn_rate"]
    for stage in profile["stages"]:
        target_users = stage["users"]
        ramp = math.ceil(abs(target_users - current_users) / spawn_rate)
        total += ramp + stage["duration_seconds"]
        current_users = target_users
    return total


def answer_payload(question):
    return {
        "question_id": question["id"], "question": question["question"],
        "type": question.get("type", "yes_no"), "answer": None,
        **{key: question.get(key) for key in
           ("learning_path_id", "module_id", "learning_unit_id")},
        "topic_id": question.get("topic_id") or question.get("related_topic_id"),
        "competency_codes": question.get("related_competency_codes", []),
    }
