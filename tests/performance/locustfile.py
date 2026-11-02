"""Enoprocesni vzdržljivostni test; zagon prek scripts/run_endurance.py."""
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

from common import ROOT, answer_payload, load_profile

PROFILE = load_profile(os.environ["PERF_PROFILE"])
RUN = Path(os.environ["PERF_RUN_DIR"])
DATA = json.loads(Path(os.environ["PERF_DATA"]).read_text(encoding="utf-8"))
PROMPTS = json.loads((ROOT / "data/assistant-prompts.json").read_text(encoding="utf-8"))
STREAM = None
NEXT_USER = 0
NEXT_SLOT = 0
STATE = {"phase": "ramp", "steady_start": None, "steady_end": None}


def record(kind, **values):
    if STREAM:
        STREAM.write(json.dumps({"kind": kind, "time": time.time(), **values}) + "\n")
        STREAM.flush()


@events.test_start.add_listener
def start(environment, **kwargs):
    global STREAM
    STREAM = (RUN / "events.jsonl").open("x", encoding="utf-8")
    record("start")


@events.request.add_listener
def request_event(request_type, name, response_time, response_length,
                  exception, context=None, **kwargs):
    record("request", group=name, ms=response_time, ok=exception is None,
           phase=STATE["phase"], cached=(context or {}).get("cached"))


@events.test_stop.add_listener
def stop(environment, **kwargs):
    record("stop", **STATE)
    if STREAM:
        STREAM.close()


@events.user_error.add_listener
def user_error(user_instance, exception, tb, **kwargs):
    record("fatal", reason="Napaka pri izvajanju uporabniškega poteka; preveri run.log.")


class EnduranceShape(LoadTestShape):
    def tick(self):
        now = time.time()
        if STATE["steady_start"] is None:
            if self.get_current_user_count() < PROFILE["users"]:
                return PROFILE["users"], PROFILE["spawn_rate"]
            STATE["steady_start"] = now + PROFILE["warmup_seconds"]
            STATE["steady_end"] = STATE["steady_start"] + PROFILE["steady_seconds"]
            record("schedule", **STATE)
        if now < STATE["steady_start"]:
            STATE["phase"] = "warmup"
        elif now < STATE["steady_end"]:
            STATE["phase"] = "steady"
        elif now < STATE["steady_end"] + PROFILE["recovery_seconds"]:
            STATE["phase"] = "recovery"
            return 0, PROFILE["users"]
        else:
            return None
        record("population", users=self.get_current_user_count(), phase=STATE["phase"])
        return PROFILE["users"], PROFILE["spawn_rate"]


class QuestionnaireUser(HttpUser):
    def on_start(self):
        global NEXT_SLOT
        self.slot = NEXT_SLOT
        NEXT_SLOT += 1
        self.rng = random.Random(PROFILE["seed"] + self.slot)

    def pause(self, key):
        gevent.sleep(self.rng.uniform(*PROFILE[key]))

    def call(self, method, path, group, validator, **kwargs):
        # Generic errors deliberately omit response bodies, tokens and signed URLs.
        with self.client.request(method, path, name=group, catch_response=True,
                                 timeout=PROFILE["timeout_seconds"], **kwargs) as response:
            try:
                value = response.json()
                valid = response.status_code == 200 and validator(value)
            except (ValueError, KeyError, TypeError, AttributeError):
                value, valid = None, False
            if not valid:
                response.failure(f"Neveljaven odgovor skupine {group}; HTTP {response.status_code}")
                return None
            if group == "voice_api":
                response.request_meta["context"]["cached"] = value["cached"]
            response.success()
            return value

    @task
    def questionnaire(self):
        global NEXT_USER
        if NEXT_USER >= len(DATA["user_ids"]):
            record("fatal", reason="Zmanjkalo je ločenih testnih profilov.")
            self.environment.process_exit_code = 2
            gevent.spawn(self.environment.runner.quit)
            raise StopUser()
        user_id = DATA["user_ids"][NEXT_USER]
        NEXT_USER += 1
        ai_user = self.slot % 20 < 8
        voice_user = self.slot % 20 == 0
        target = self.rng.choice(DATA["targets"])
        record("journey_start", ai=ai_user, voice=voice_user)
        questionnaire = self.call("GET", "/api/questionnaires", "ordinary/questionnaire",
            lambda v: v["target_id"] == target["target_id"] and
            v["target_type"] == target["target_type"] and bool(v["questions"]) and
            all(q["id"] and q["question"] and q.get("type", "yes_no") == "yes_no"
                for q in v["questions"]), params={**target, "user_id": user_id})
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
            context = {key: question.get(key) or
                       (target["target_id"] if target["target_type"] == key.removesuffix("_id") else None)
                       for key in ("learning_path_id", "module_id", "learning_unit_id")}
            for _ in range(ai_indices.count(index)):
                result = self.call("POST", "/api/assessment-assistant/message", "ai",
                    lambda v: bool(v["session_id"]) and isinstance(v["answer"], str) and bool(v["answer"].strip()),
                    json={**context, "session_id": session_id, "user_id": user_id,
                          "question_id": question["id"], "question_text": question["question"],
                          "answer_options": ["Da", "Ne"], "user_message": self.rng.choice(PROMPTS)})
                if result:
                    session_id = result["session_id"]
                self.pause("assistant_read_seconds")
            if index == voice_index:
                result = self.call("POST", "/api/voice-help/question", "voice_api",
                    lambda v: isinstance(v["cached"], bool) and bool(v["help_text"]) and bool(v["audio_url"]),
                    json={**target, "question_id": question["id"], "question_text": question["question"],
                          "answer_options": ["Da", "Ne"], "locale": "sl-SI", "voice_name": "sl-SI-PetraNeural"})
                if result:
                    # Allowlist is provided explicitly; never log the returned signed URL.
                    audio = urlsplit(result["audio_url"])
                    if audio.scheme == "https" and audio.hostname in DATA["audio_hosts"]:
                        started = time.perf_counter()
                        error = None
                        size = 0
                        try:
                            # A separate session avoids Locust storing the signed URL in failures.
                            with requests.Session() as audio_client:
                                response = audio_client.get(result["audio_url"], allow_redirects=False,
                                                            timeout=PROFILE["timeout_seconds"])
                                size = len(response.content)
                                if response.status_code != 200 or not size or not response.headers.get("Content-Type", "").startswith("audio/"):
                                    error = RuntimeError("Zvočni posnetek ni dosegljiv.")
                        except requests.RequestException:
                            error = RuntimeError("Prenos zvočnega posnetka ni uspel.")
                        self.environment.events.request.fire(request_type="GET", name="voice_audio",
                            response_time=(time.perf_counter() - started)*1000,
                            response_length=size, exception=error, context={})
                        record("voice_delivery", cached=result["cached"],
                               ms=(time.perf_counter() - started) * 1000)
                    else:
                        record("fatal", reason="Zvočni naslov ni na dovoljenem seznamu.")
                    self.pause("assistant_read_seconds")
            answer = answer_payload(question)
            answer.update(context)
            answer["answer"] = self.rng.choice([True, False])
            answers.append(answer)
        result = self.call("POST", "/api/assessments/evaluate", "ordinary/evaluate",
            lambda v: v["user_id"] == user_id and v["target_id"] == target["target_id"]
            and v["target_type"] == target["target_type"] and isinstance(v["learning_unit_results"], list),
            json={**target, "user_id": user_id, "answers": answers})
        record("journey_end", ok=result is not None, ai_messages=ai_count)
