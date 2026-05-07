import os
from celery import Celery
from dotenv import load_dotenv

load_dotenv()

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
REDIS_BACKEND = REDIS_URL.rstrip("/0123456789").rstrip("/") + "/1"

celery_app = Celery(
    "pod",
    broker=REDIS_URL,
    backend=REDIS_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    result_expires=3600,
    task_track_started=True,
    # Each skill task gets a content-hash as its task_id — deduplication is free
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)
