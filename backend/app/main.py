import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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

app = FastAPI(
    title="Pod Manufacturing API",
    version="0.1.0",
    description="Parametric pod manufacturing — compliance, production packs, IFC export.",
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
