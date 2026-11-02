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


def answer_payload(question):
    return {
        "question_id": question["id"], "question": question["question"],
        "type": question.get("type", "yes_no"), "answer": None,
        **{key: question.get(key) for key in
           ("learning_path_id", "module_id", "learning_unit_id")},
        "topic_id": question.get("topic_id") or question.get("related_topic_id"),
        "competency_codes": question.get("related_competency_codes", []),
    }
