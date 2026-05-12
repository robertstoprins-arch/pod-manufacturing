import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logger = logging.getLogger(__name__)


def _run_migrations():
    """Run alembic upgrade head at startup so new tables are always present."""
    try:
        from alembic.config import Config
        from alembic import command
        # alembic.ini lives one directory above this package (in backend/)
        backend_dir = os.path.dirname(os.path.dirname(__file__))
        cfg = Config(os.path.join(backend_dir, "alembic.ini"))
        command.upgrade(cfg, "head")
        logger.info("Alembic migrations applied.")
    except Exception as exc:
        logger.warning("Alembic migration skipped or failed: %s", exc)


@asynccontextmanager
async def lifespan(app):
    _run_migrations()
    yield
from app.api.health import router as health_router
from app.api.pods import router as pods_router
from app.api.drawings import router as drawings_router
from app.api.workspaces import router as workspaces_router
from app.api.build_ups import router as build_ups_router
from app.api.pod_specs import router as pod_specs_router
from app.api.material_prices import router as material_prices_router
from app.api.provisional_allowances import router as provisional_allowances_router
from app.api.settings import router as settings_router
from app.api.finish_catalogue import router as finish_catalogue_router
from app.api.finish_packages import router as finish_packages_router
from app.api.clients import router as clients_router
from app.api.quotes import router as quotes_router
from app.api.suppliers import router as suppliers_router

app = FastAPI(
    title="Pod Manufacturing API",
    version="0.1.0",
    description="Parametric pod manufacturing — compliance, production packs, IFC export.",
    lifespan=lifespan,
)

_origins_env = os.environ.get(
    "CORS_ORIGINS",
    "http://localhost:5173,http://localhost:5174,http://localhost:4173",
)
_origins = [o.strip() for o in _origins_env.split(",") if o.strip()]

# Also allow all Vercel preview deployments for this project
_origin_regex = (
    r"https://pod-manufacturing(-[a-z0-9]+)*(-robertstoprins-7454s-projects)?\.vercel\.app"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_origin_regex=_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(pods_router)
app.include_router(drawings_router)
app.include_router(workspaces_router)
app.include_router(build_ups_router)
app.include_router(pod_specs_router)
app.include_router(material_prices_router)
app.include_router(provisional_allowances_router)
app.include_router(settings_router)
app.include_router(finish_catalogue_router)
app.include_router(finish_packages_router)
app.include_router(clients_router)
app.include_router(quotes_router)
app.include_router(suppliers_router)


@app.get("/ping", tags=["health"])
def ping():
    return {"ok": True}
