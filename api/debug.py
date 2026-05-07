"""Standalone diagnostic — no db import, just reports env state."""
import os
from fastapi import FastAPI

app = FastAPI()

@app.get("/api/debug")
def debug():
    db_url = os.environ.get("DATABASE_URL", "<NOT SET>")
    # Mask password for safety
    if db_url and "://" in db_url:
        parts = db_url.split("@")
        masked = parts[0][:25] + "***@" + parts[-1] if len(parts) > 1 else db_url[:20] + "..."
    else:
        masked = db_url[:30] if db_url else "<NOT SET>"
    return {
        "DATABASE_URL": masked,
        "DATABASE_URL_len": len(db_url),
        "has_DATABASE_URL": "DATABASE_URL" in os.environ,
        "CLERK_JWKS_URL": os.environ.get("CLERK_JWKS_URL", "<NOT SET>")[:40],
        "env_keys": [k for k in os.environ if not k.startswith("LD_") and k.upper() == k][:20],
    }
