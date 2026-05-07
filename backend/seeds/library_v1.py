"""Seed: Library Version 1.0.0

Run with:  python -m seeds.library_v1
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from datetime import datetime, timezone
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

load_dotenv()
from app.models import LibraryVersion

engine = create_engine(os.environ["DATABASE_URL"])
Session = sessionmaker(bind=engine)


def seed():
    with Session() as db:
        existing = db.query(LibraryVersion).filter_by(version="1.0.0").first()
        if existing:
            print("LibraryVersion 1.0.0 already exists — skipping.")
            return existing.id

        lv = LibraryVersion(
            version="1.0.0",
            released_at=datetime(2026, 4, 29, tzinfo=timezone.utc),
            notes="Initial material library — Nordic + Latvian materials, EN ISO 14683 junction psi-values.",
        )
        db.add(lv)
        db.commit()
        db.refresh(lv)
        print(f"Inserted LibraryVersion 1.0.0 (id={lv.id})")
        return lv.id


if __name__ == "__main__":
    seed()
