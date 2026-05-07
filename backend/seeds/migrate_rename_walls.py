"""
One-shot migration: rename build-ups to match the updated library naming.

Run once against an existing database:
    python seeds/migrate_rename_walls.py

Safe to re-run — skips any rename where the source name no longer exists.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.db import engine
from app.models import BuildUp

RENAMES: list[tuple[str, str]] = [
    (
        "Nordic Enhanced Wall — Closed Panel",
        "Nordic Enhanced PIR Wall — Closed Panel",
    ),
]


def run() -> None:
    with Session(engine) as db:
        for old_name, new_name in RENAMES:
            row = db.query(BuildUp).filter_by(name=old_name).first()
            if row is None:
                print(f"  skip (not found): {old_name!r}")
                continue
            # Guard: don't stomp if the target name already exists
            if db.query(BuildUp).filter_by(name=new_name).first():
                print(f"  skip (target exists): {new_name!r}")
                continue
            row.name = new_name
            print(f"  renamed: {old_name!r} → {new_name!r}")
        db.commit()
    print("Done.")


if __name__ == "__main__":
    run()
