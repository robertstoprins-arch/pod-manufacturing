"""Add selected_finishes_json column to pod_specs table."""
import sys
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv('../.env')
from app.db import engine
from sqlalchemy import text

with engine.begin() as conn:
    try:
        conn.execute(text(
            "ALTER TABLE pod_specs ADD COLUMN selected_finishes_json JSON"
        ))
        print("Column added: pod_specs.selected_finishes_json")
    except Exception as e:
        if "already exists" in str(e).lower() or "duplicate column" in str(e).lower():
            print("Column already exists — skipping.")
        else:
            raise
