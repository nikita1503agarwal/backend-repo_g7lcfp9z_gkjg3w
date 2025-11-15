"""
Simple worker process for competitions service.
This worker polls the `job` collection and processes jobs like `post_registration`.
It can be run as a standalone script: `python worker.py`
"""
import os
import time
from datetime import datetime, timezone, timedelta
from typing import Optional
from bson.objectid import ObjectId

from database import db

POLL_INTERVAL = int(os.getenv("WORKER_POLL_INTERVAL", "5"))
BATCH_SIZE = int(os.getenv("WORKER_BATCH_SIZE", "10"))


def log(msg: str):
    print(f"[worker] {datetime.now(timezone.utc).isoformat()} | {msg}")


def fetch_pending_job() -> Optional[dict]:
    # Atomically claim one pending job by setting status to processing
    job = db["job"].find_one_and_update(
        {"status": "pending"},
        {"$set": {"status": "processing", "started_at": datetime.now(timezone.utc)}},
    )
    return job


def process_post_registration(job: dict):
    payload = job.get("payload", {})
    reg_id = payload.get("registration_id")
    event_id = payload.get("event_id")
    if not reg_id or not event_id:
        raise ValueError("Missing registration_id or event_id in payload")

    # Generate confirmation code and mark registration confirmed
    code = f"CONF-{str(reg_id)[-6:].upper()}"
    db["registration"].update_one(
        {"_id": ObjectId(reg_id)},
        {"$set": {"status": "confirmed", "confirmation_code": code, "updated_at": datetime.now(timezone.utc)}},
    )
    # In a real system, send email here. We'll just write an outbox record.
    db["outbox"].insert_one(
        {
            "type": "email",
            "to": db["registration"].find_one({"_id": ObjectId(reg_id)}).get("participant_email"),
            "subject": "Registration confirmed",
            "body": f"Your registration for event {event_id} is confirmed. Code: {code}",
            "created_at": datetime.now(timezone.utc),
        }
    )


def process_job(job: dict):
    try:
        jtype = job.get("type")
        if jtype == "post_registration":
            process_post_registration(job)
        else:
            raise ValueError(f"Unknown job type: {jtype}")
        db["job"].update_one({"_id": job["_id"]}, {"$set": {"status": "done", "finished_at": datetime.now(timezone.utc)}})
        log(f"Processed job {job['_id']}")
    except Exception as e:
        db["job"].update_one({"_id": job["_id"]}, {"$set": {"status": "failed", "error": str(e), "finished_at": datetime.now(timezone.utc)}})
        log(f"Failed job {job['_id']}: {e}")


def run():
    log("Worker starting")
    while True:
        processed = 0
        for _ in range(BATCH_SIZE):
            job = fetch_pending_job()
            if not job:
                break
            process_job(job)
            processed += 1
        if processed == 0:
            time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    run()
