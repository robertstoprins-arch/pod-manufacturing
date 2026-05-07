"""Create account_settings table and seed defaults."""
import sys
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv('../.env')
from app.db import engine, SessionLocal
from app.models import Base, AccountSettings

Base.metadata.create_all(engine, tables=[AccountSettings.__table__])
print("Table created.")

db = SessionLocal()
try:
    existing = db.query(AccountSettings).first()
    if not existing:
        db.add(AccountSettings(
            default_markup_percent=50.0,
            currency="EUR",
            vat_rate_percent=21.0,
            vat_mode="excluded",
            round_to_nearest=100,
        ))
        db.commit()
        print("Seeded default account settings.")
    else:
        print(f"Settings already exist (id={existing.id}).")
finally:
    db.close()
