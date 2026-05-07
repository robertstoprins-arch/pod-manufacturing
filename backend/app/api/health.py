import os
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
import redis as redis_lib

from app.db import get_db

router = APIRouter(tags=["system"])


@router.get("/env-debug")
def env_debug():
    """Returns masked env state — for diagnosing Vercel deployment."""
    db_url = os.environ.get("DATABASE_URL", "")
    masked = ""
    if db_url and "@" in db_url:
        parts = db_url.split("@")
        masked = parts[0][:20] + "***@" + parts[-1]
    elif db_url:
        masked = db_url[:30] + "..."
    else:
        masked = "<NOT SET>"
    return {
        "DATABASE_URL_masked": masked,
        "DATABASE_URL_len": len(db_url),
        "DATABASE_URL_empty": db_url == "",
        "CLERK_JWKS_URL_set": bool(os.environ.get("CLERK_JWKS_URL")),
        "REDIS_URL_set": bool(os.environ.get("REDIS_URL")),
    }


@router.get("/health")
def health_check(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as exc:
        db_status = f"error: {exc}"

    try:
        r = redis_lib.from_url(os.environ.get("REDIS_URL", "redis://localhost:6379/0"), socket_connect_timeout=2)
        r.ping()
        redis_status = "connected"
    except Exception as exc:
        redis_status = f"error: {exc}"

    overall = "ok" if db_status == "connected" and redis_status == "connected" else "degraded"
    return {"status": overall, "db": db_status, "redis": redis_status}
