"""
Simple scheduled cron job for competitions service.
This job scans upcoming events and generates reminder jobs 24 hours before start.
Run once per minute via cron or a scheduler.
"""
import os
from datetime import datetime, timezone, timedelta
from database import db

REMINDER_WINDOW_HOURS = int(os.getenv("REMINDER_WINDOW_HOURS", "24"))


def main():
    now = datetime.now(timezone.utc)
    window_start = now + timedelta(hours=REMINDER_WINDOW_HOURS)
    window_end = now + timedelta(hours=REMINDER_WINDOW_HOURS + 1)

    # Find events starting around the reminder window and that are published
    events = db["event"].find({
        "is_published": True,
        "start_at": {"$gte": window_start, "$lt": window_end},
    })

    for ev in events:
        # For each registration without a reminder job yet, enqueue
        regs = db["registration"].find({"event_id": str(ev["_id"]), "status": {"$ne": "cancelled"}})
        for reg in regs:
            exists = db["job"].count_documents({
                "type": "send_reminder",
                "payload.registration_id": str(reg["_id"]),
            })
            if exists:
                continue
            db["job"].insert_one({
                "type": "send_reminder",
                "payload": {
                    "registration_id": str(reg["_id"]),
                    "event_id": str(ev["_id"]),
                },
                "status": "pending",
                "created_at": now,
            })


if __name__ == "__main__":
    main()
