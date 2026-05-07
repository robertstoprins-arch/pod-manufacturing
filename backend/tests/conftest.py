"""
Pytest fixtures for the pod manufacturing backend.

Uses SQLite in-memory so tests run without Docker — no postgres needed.
SQLAlchemy maps JSONB → TEXT and UUID → VARCHAR on SQLite, which is fine
for logic tests. The migration file is NOT run here; we use metadata.create_all
directly, which is faster and sidesteps dialect differences in Alembic scripts.
"""
import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models import Base


@pytest.fixture(scope="function")
def engine():
    eng = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,   # single connection — required for TestClient threads
    )

    # Enable FK enforcement in SQLite (off by default)
    @event.listens_for(eng, "connect")
    def _set_pragma(dbapi_conn, _record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(eng)
    yield eng
    Base.metadata.drop_all(eng)


@pytest.fixture(scope="function")
def db(engine):
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = Session()
    yield session
    session.rollback()
    session.close()
