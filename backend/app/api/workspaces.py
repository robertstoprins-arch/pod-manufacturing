"""
API: Workspace — authenticated CRUD for orgs, projects, and pods.

All routes require a valid Clerk JWT (via require_auth).

POST /me/org/provision          — create org from Clerk org_id (idempotent)
GET  /me/org                    — get current org
POST /projects                  — create a project in the current org
GET  /projects                  — list projects in the current org
GET  /projects/{id}             — get a single project
POST /projects/{id}/pods        — decompose + persist a pod
GET  /projects/{id}/pods        — list pods in a project
GET  /projects/{id}/pods/{pod_id} — get a pod with its elements
"""
import re
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.auth import ClerkClaims, require_auth
from app.db import get_db
from app.models import Element, Organization, Pod, Project
from app.skills.element_decomposer import DecompositionError, OpeningSpec, decompose_pod
from app.api.pods import OpeningIn, PodGeometryIn

router = APIRouter(tags=["workspace"])


# ── Helpers ───────────────────────────────────────────────────────────────────

def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:100]


def _require_org(claims: ClerkClaims, db: Session) -> Organization:
    """Return the org for the current Clerk session. 404 if not provisioned yet."""
    if not claims.org_id:
        raise HTTPException(
            status_code=400,
            detail="No org context in token. Use an org-scoped Clerk session.",
        )
    org = db.query(Organization).filter_by(clerk_org_id=claims.org_id).first()
    if org is None:
        raise HTTPException(
            status_code=404,
            detail="Org not provisioned. POST /me/org/provision first.",
        )
    return org


# ── Response models ───────────────────────────────────────────────────────────

class OrgOut(BaseModel):
    id: str
    name: str
    slug: str
    clerk_org_id: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class ProjectIn(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    address: Optional[str] = None
    jurisdiction_profile_id: int = Field(..., description="ID from jurisdiction_profiles table")
    library_version_id: int = Field(..., description="ID from library_versions table")


class ProjectOut(BaseModel):
    id: str
    name: str
    address: Optional[str]
    jurisdiction_profile_id: int
    library_version_id: int
    created_by: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class PodIn(PodGeometryIn):
    name: str = Field(..., min_length=1, max_length=255)


class ElementOut(BaseModel):
    id: str
    type: str
    area_gross_m2: Optional[float]
    area_net_m2: Optional[float]
    perimeter_m: Optional[float]
    geometry: Optional[dict]

    model_config = ConfigDict(from_attributes=True)


class PodOut(BaseModel):
    id: str
    name: str
    geometry_2d: Optional[dict]
    elements: list[ElementOut] = []

    model_config = ConfigDict(from_attributes=True)


# ── POST /me/org/provision ────────────────────────────────────────────────────

class ProvisionIn(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)


@router.post("/me/org/provision", response_model=OrgOut, status_code=201)
def provision_org(
    body: ProvisionIn,
    claims: ClerkClaims = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """
    Idempotent — call on first login. Creates the organization row linked
    to the Clerk org_id. If it already exists, returns the existing record.
    """
    if not claims.org_id:
        raise HTTPException(
            status_code=400,
            detail="No org context in token. Activate an org in Clerk first.",
        )
    existing = db.query(Organization).filter_by(clerk_org_id=claims.org_id).first()
    if existing:
        return _org_out(existing)

    base_slug = _slug(body.name)
    slug = base_slug
    counter = 1
    while db.query(Organization).filter_by(slug=slug).first():
        slug = f"{base_slug}-{counter}"
        counter += 1

    org = Organization(
        id=uuid.uuid4(),
        clerk_org_id=claims.org_id,
        name=body.name,
        slug=slug,
    )
    db.add(org)
    db.commit()
    db.refresh(org)
    return _org_out(org)


def _org_out(org: Organization) -> OrgOut:
    return OrgOut(
        id=str(org.id),
        name=org.name,
        slug=org.slug,
        clerk_org_id=org.clerk_org_id,
    )


# ── GET /me/org ───────────────────────────────────────────────────────────────

@router.get("/me/org", response_model=OrgOut)
def get_org(
    claims: ClerkClaims = Depends(require_auth),
    db: Session = Depends(get_db),
):
    org = _require_org(claims, db)
    return _org_out(org)


# ── POST /projects ────────────────────────────────────────────────────────────

@router.post("/projects", response_model=ProjectOut, status_code=201)
def create_project(
    body: ProjectIn,
    claims: ClerkClaims = Depends(require_auth),
    db: Session = Depends(get_db),
):
    org = _require_org(claims, db)
    project = Project(
        id=uuid.uuid4(),
        organization_id=org.id,
        name=body.name,
        address=body.address,
        jurisdiction_profile_id=body.jurisdiction_profile_id,
        library_version_id=body.library_version_id,
        created_by=claims.user_id,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return _project_out(project)


def _project_out(p: Project) -> ProjectOut:
    return ProjectOut(
        id=str(p.id),
        name=p.name,
        address=p.address,
        jurisdiction_profile_id=p.jurisdiction_profile_id,
        library_version_id=p.library_version_id,
        created_by=p.created_by,
    )


# ── GET /projects ─────────────────────────────────────────────────────────────

@router.get("/projects", response_model=list[ProjectOut])
def list_projects(
    claims: ClerkClaims = Depends(require_auth),
    db: Session = Depends(get_db),
):
    org = _require_org(claims, db)
    projects = db.query(Project).filter_by(organization_id=org.id).all()
    return [_project_out(p) for p in projects]


# ── GET /projects/{id} ────────────────────────────────────────────────────────

@router.get("/projects/{project_id}", response_model=ProjectOut)
def get_project(
    project_id: str,
    claims: ClerkClaims = Depends(require_auth),
    db: Session = Depends(get_db),
):
    org = _require_org(claims, db)
    project = _get_project_or_404(project_id, org.id, db)
    return _project_out(project)


def _get_project_or_404(project_id: str, org_id, db: Session) -> Project:
    try:
        pid = uuid.UUID(project_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Project not found")
    project = db.query(Project).filter_by(id=pid, organization_id=org_id).first()
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


# ── POST /projects/{id}/pods ──────────────────────────────────────────────────

@router.post("/projects/{project_id}/pods", response_model=PodOut, status_code=201)
def create_pod(
    project_id: str,
    body: PodIn,
    claims: ClerkClaims = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """
    Decompose the pod geometry and persist the pod + all elements to the DB.
    Returns the saved pod with its element list.
    """
    org = _require_org(claims, db)
    project = _get_project_or_404(project_id, org.id, db)

    try:
        openings = [
            OpeningSpec(
                wall=o.wall, type=o.type,
                width_m=o.width_m, height_m=o.height_m,
                sill_height_m=o.sill_height_m,
                x_offset_m=o.x_offset_m,
                shape=o.shape,
            )
            for o in body.openings
        ]
        decomposed = decompose_pod(
            width_m=body.width_m,
            length_m=body.length_m,
            wall_height_m=body.wall_height_m,
            roof_type=body.roof_type,
            roof_pitch_deg=body.roof_pitch_deg,
            openings=openings,
        )
    except DecompositionError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    geometry_2d = {
        "width_m": body.width_m,
        "length_m": body.length_m,
        "wall_height_m": body.wall_height_m,
        "roof_type": body.roof_type,
        "roof_pitch_deg": body.roof_pitch_deg,
        "openings": [
            {
                "wall": o.wall, "type": o.type,
                "width_m": o.width_m, "height_m": o.height_m,
                "sill_height_m": o.sill_height_m,
            }
            for o in openings
        ],
    }

    pod = Pod(
        id=uuid.uuid4(),
        project_id=project.id,
        name=body.name,
        geometry_2d=geometry_2d,
    )
    db.add(pod)
    db.flush()  # assign pod.id before inserting elements

    elements = []
    for e in decomposed:
        elem = Element(
            id=uuid.uuid4(),
            pod_id=pod.id,
            type=e.type,
            geometry=e.geometry,
            area_gross_m2=e.area_gross_m2,
            area_net_m2=e.area_net_m2,
            perimeter_m=e.perimeter_m,
        )
        db.add(elem)
        elements.append(elem)

    db.commit()
    db.refresh(pod)

    return PodOut(
        id=str(pod.id),
        name=pod.name,
        geometry_2d=pod.geometry_2d,
        elements=[
            ElementOut(
                id=str(e.id),
                type=e.type,
                area_gross_m2=e.area_gross_m2,
                area_net_m2=e.area_net_m2,
                perimeter_m=e.perimeter_m,
                geometry=e.geometry,
            )
            for e in elements
        ],
    )


# ── GET /projects/{id}/pods ───────────────────────────────────────────────────

@router.get("/projects/{project_id}/pods", response_model=list[PodOut])
def list_pods(
    project_id: str,
    claims: ClerkClaims = Depends(require_auth),
    db: Session = Depends(get_db),
):
    org = _require_org(claims, db)
    project = _get_project_or_404(project_id, org.id, db)
    pods = db.query(Pod).filter_by(project_id=project.id).all()
    return [
        PodOut(
            id=str(p.id),
            name=p.name,
            geometry_2d=p.geometry_2d,
            elements=[],  # summary list — no elements for performance
        )
        for p in pods
    ]


# ── GET /projects/{id}/pods/{pod_id} ─────────────────────────────────────────

@router.get("/projects/{project_id}/pods/{pod_id}", response_model=PodOut)
def get_pod(
    project_id: str,
    pod_id: str,
    claims: ClerkClaims = Depends(require_auth),
    db: Session = Depends(get_db),
):
    org = _require_org(claims, db)
    project = _get_project_or_404(project_id, org.id, db)
    try:
        pid = uuid.UUID(pod_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Pod not found")
    pod = db.query(Pod).filter_by(id=pid, project_id=project.id).first()
    if pod is None:
        raise HTTPException(status_code=404, detail="Pod not found")

    elements = db.query(Element).filter_by(pod_id=pod.id).all()
    return PodOut(
        id=str(pod.id),
        name=pod.name,
        geometry_2d=pod.geometry_2d,
        elements=[
            ElementOut(
                id=str(e.id),
                type=e.type,
                area_gross_m2=e.area_gross_m2,
                area_net_m2=e.area_net_m2,
                perimeter_m=e.perimeter_m,
                geometry=e.geometry,
            )
            for e in elements
        ],
    )
