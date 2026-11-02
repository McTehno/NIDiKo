"""Po arhiviranju rezultatov odstrani samo podatke evidentiranega sklopa."""
import argparse
import json
import os
from pathlib import Path


def main():
    from pymongo import MongoClient
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("data", type=Path)
    parser.add_argument("--confirm-pool", required=True)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    data = json.loads(args.data.read_text(encoding="utf-8"))
    pool = data["pool_id"]
    if not pool.startswith("perf_") or args.confirm_pool != pool or os.environ["PERF_DATABASE_NAME"] != data["database"]:
        parser.error("Sklop ali baza se ne ujemata.")
    ids = data["user_ids"]
    if not ids or not all(uid.startswith("user_" + pool + "_") for uid in ids):
        parser.error("Neveljavna evidenca uporabnikov.")
    client = MongoClient(os.environ["PERF_MONGODB_URI"], serverSelectionTimeoutMS=10000)
    database = client[data["database"]]
    sessions = list(database.assessment_assistant_sessions.find({"user_id": {"$in": ids}}, {"session_id": 1}))
    session_ids = [s["session_id"] for s in sessions]
    print(f"Profili v evidenci: {len(ids)}, AI seje: {len(session_ids)}, izvedba: {args.execute}")
    if args.execute:
        database.assessment_assistant_messages.delete_many({"session_id": {"$in": session_ids}})
        database.assessment_assistant_sessions.delete_many({"user_id": {"$in": ids}})
        database.users.delete_many({"_id": {"$in": ids}, "performance_pool_id": pool})
    client.close()


if __name__ == "__main__":
    main()
