import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# override=False ensures Vercel-injected env vars are never overwritten by a bundled .env file
load_dotenv(override=False)

_engine = None
_SessionLocal = None


def _get_engine():
    global _engine
    if _engine is None:
        db_url = os.environ.get("DATABASE_URL", "")
        if not db_url:
            raise RuntimeError(
                "DATABASE_URL is not configured. Set it in your deployment environment."
            )
        _engine = create_engine(db_url, pool_pre_ping=True)
    return _engine


def _get_session_local():
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=_get_engine(), autoflush=False, autocommit=False)
    return _SessionLocal


def get_db():
    db = _get_session_local()()
    try:
        yield db
    finally:
        db.close()


def check_db_connection() -> bool:
    try:
        with _get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Seed-script compatibility shims
# Seeds do: from app.db import engine, SessionLocal
# We expose thin callables/proxies that resolve on first use.
# ---------------------------------------------------------------------------

import sys as _sys
import types as _types


class _DbModule(_types.ModuleType):
    """Module subclass so `engine` and `SessionLocal` resolve lazily."""

    @property
    def engine(self):
        return _get_engine()

    @property
    def SessionLocal(self):
        return _get_session_local()


# Replace this module in sys.modules with the subclass instance
_mod = _DbModule(__name__)
_mod.__dict__.update({k: v for k, v in globals().items() if not k.startswith("_")})
_mod._get_engine = _get_engine
_mod._get_session_local = _get_session_local
_mod.get_db = get_db
_mod.check_db_connection = check_db_connection
_mod.__file__ = __file__
_mod.__spec__ = __spec__
_sys.modules[__name__] = _mod
