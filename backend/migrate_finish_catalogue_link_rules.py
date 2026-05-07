"""
Add specification_url_public column to finish_catalogue_items.

Rules enforced:
  supplier_url         — always internal (purchasing reference only)
  specification_url    — shown in client PDF only if specification_url_public=True
  datasheet_url        — shown in client PDF only if specification_url_public=True
  image_url            — shown to customers only if image_approval_status in CUSTOMER_SAFE set

Run from backend/:
    python migrate_finish_catalogue_link_rules.py
"""
import sys
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv('../.env')
from app.db import engine
from sqlalchemy import text

with engine.begin() as conn:
    try:
        conn.execute(text(
            "ALTER TABLE finish_catalogue_items "
            "ADD COLUMN specification_url_public BOOLEAN NOT NULL DEFAULT FALSE"
        ))
        print("Column added: finish_catalogue_items.specification_url_public")
    except Exception as e:
        if "already exists" in str(e).lower() or "duplicate column" in str(e).lower():
            print("Column already exists — skipping.")
        else:
            raise
