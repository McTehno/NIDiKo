"""Pripravi sintetične aplikacijske profile v izrecno izbrani testni bazi."""
import argparse
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path


def main():
    from pymongo import MongoClient
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=5000)
    parser.add_argument("--target-id", required=True, help="ID obstoječe učne poti")
    parser.add_argument("--audio-host", action="append", required=True, help="Dovoljena domena Azure Blob, brez https://")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--confirm-database", required=True)
    args = parser.parse_args()
    database_name = os.environ["PERF_DATABASE_NAME"]
    if args.confirm_database != database_name or not any(word in database_name.lower() for word in ("test", "staging")):
        parser.error("Potrdi namensko testno oziroma staging bazo.")
    if args.output.exists() or args.count <= 0:
        parser.error("Izhod že obstaja ali število ni pozitivno.")
    client = MongoClient(os.environ["PERF_MONGODB_URI"], serverSelectionTimeoutMS=10000)
    database = client[database_name]
    client.admin.command("ping")
    pool_id = "perf_" + uuid.uuid4().hex
    ids = [f"user_{pool_id}_{i}" for i in range(args.count)]
    # Write recovery inventory BEFORE inserting, so a partial failure remains cleanable.
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({"pool_id": pool_id, "database": database_name,
        "user_ids": ids, "targets": [{"target_type": "learning_path", "target_id": args.target_id}],
        "audio_hosts": args.audio_host}, indent=2), encoding="utf-8")
    now = datetime.now(timezone.utc)
    for offset in range(0, len(ids), 500):
        database.users.insert_many([{
            "_id": user_id, "auth_user_id": user_id, "auth_provider": "performance_test",
            "name": "Sintetični testni uporabnik", "email": f"{user_id}@example.invalid",
            "performance_pool_id": pool_id, "created_at": now, "updated_at": now,
            "progress": {"saved": {"learning_path_ids": [], "module_ids": [], "learning_unit_ids": []},
                         "favorites": {"learning_path_ids": [], "module_ids": [], "learning_unit_ids": []},
                         "completed": {"learning_path_ids": [], "module_ids": [], "learning_unit_ids": []},
                         "current_positions": [], "questionnaire_answers": []}
        } for user_id in ids[offset:offset+500]])
    client.close()
    print(f"Pripravljenih profilov: {len(ids)}. Evidenca: {args.output}")


if __name__ == "__main__":
    main()
