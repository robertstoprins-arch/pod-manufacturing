"""
Tests for workspace endpoints: org provision, projects, pods.

Auth is mocked — ClerkClaims injected via FastAPI dependency override.
DB uses the SQLite in-memory fixture from conftest.
"""
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.auth import ClerkClaims, require_auth
from app.db import get_db
from app.models import JurisdictionProfile, LibraryVersion


# ── Auth + DB overrides ───────────────────────────────────────────────────────

ORG_CLAIMS  = ClerkClaims(user_id="user_aaa", org_id="org_aaa", org_role="admin")
ORG2_CLAIMS = ClerkClaims(user_id="user_bbb", org_id="org_bbb", org_role="admin")
NO_ORG_CLAIMS = ClerkClaims(user_id="user_ccc", org_id=None, org_role=None)


def _make_client(db_session: Session, claims: ClerkClaims) -> TestClient:
    app.dependency_overrides[require_auth] = lambda: claims
    app.dependency_overrides[get_db] = lambda: db_session
    return TestClient(app, raise_server_exceptions=True)


@pytest.fixture
def seed_refs(db):
    """Insert minimal JurisdictionProfile + LibraryVersion rows needed for projects."""
    jp = JurisdictionProfile(
        version="2024", country="SE", code="BBR",
        u_value_wall=0.18, u_value_roof=0.13, u_value_floor=0.15,
        u_value_window=1.2, airtightness_target=1.5,
    )
    lv = LibraryVersion(version="v1.0")
    db.add_all([jp, lv])
    db.commit()
    db.refresh(jp)
    db.refresh(lv)
    return {"jp_id": jp.id, "lv_id": lv.id}


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.clear()


# ── POST /me/org/provision ────────────────────────────────────────────────────

def test_provision_creates_org(db):
    client = _make_client(db, ORG_CLAIMS)
    r = client.post("/me/org/provision", json={"name": "Timber Works AS"})
    assert r.status_code == 201
    body = r.json()
    assert body["name"] == "Timber Works AS"
    assert body["clerk_org_id"] == "org_aaa"
    assert body["slug"] == "timber-works-as"

def test_provision_is_idempotent(db):
    client = _make_client(db, ORG_CLAIMS)
    r1 = client.post("/me/org/provision", json={"name": "Timber Works AS"})
    r2 = client.post("/me/org/provision", json={"name": "Timber Works AS"})
    assert r1.status_code == 201
    assert r2.status_code == 201
    assert r1.json()["id"] == r2.json()["id"]

def test_provision_without_org_context_returns_400(db):
    client = _make_client(db, NO_ORG_CLAIMS)
    r = client.post("/me/org/provision", json={"name": "Solo"})
    assert r.status_code == 400

def test_provision_slug_deduplication(db):
    client = _make_client(db, ORG_CLAIMS)
    client.post("/me/org/provision", json={"name": "Timber Works AS"})
    client2 = _make_client(db, ORG2_CLAIMS)
    r2 = client2.post("/me/org/provision", json={"name": "Timber Works AS"})
    assert r2.status_code == 201
    assert r2.json()["slug"] != "timber-works-as"   # deduplicated


# ── GET /me/org ───────────────────────────────────────────────────────────────

def test_get_org_returns_org(db):
    client = _make_client(db, ORG_CLAIMS)
    client.post("/me/org/provision", json={"name": "Timber Works AS"})
    r = client.get("/me/org")
    assert r.status_code == 200
    assert r.json()["clerk_org_id"] == "org_aaa"

def test_get_org_not_provisioned_returns_404(db):
    client = _make_client(db, ORG_CLAIMS)
    r = client.get("/me/org")
    assert r.status_code == 404


# ── POST /projects ────────────────────────────────────────────────────────────

def test_create_project(db, seed_refs):
    client = _make_client(db, ORG_CLAIMS)
    client.post("/me/org/provision", json={"name": "Timber Works AS"})
    r = client.post("/projects", json={
        "name": "Oslo Student Housing",
        "jurisdiction_profile_id": seed_refs["jp_id"],
        "library_version_id": seed_refs["lv_id"],
    })
    assert r.status_code == 201
    body = r.json()
    assert body["name"] == "Oslo Student Housing"
    assert body["created_by"] == "user_aaa"

def test_create_project_requires_org(db, seed_refs):
    client = _make_client(db, NO_ORG_CLAIMS)
    r = client.post("/projects", json={
        "name": "Test",
        "jurisdiction_profile_id": seed_refs["jp_id"],
        "library_version_id": seed_refs["lv_id"],
    })
    assert r.status_code in (400, 404)


# ── GET /projects ─────────────────────────────────────────────────────────────

def test_list_projects_empty(db, seed_refs):
    client = _make_client(db, ORG_CLAIMS)
    client.post("/me/org/provision", json={"name": "Timber Works AS"})
    r = client.get("/projects")
    assert r.status_code == 200
    assert r.json() == []

def test_list_projects_returns_own_only(db, seed_refs):
    # Org A creates a project; org B should not see it
    clientA = _make_client(db, ORG_CLAIMS)
    clientA.post("/me/org/provision", json={"name": "Org A"})
    clientA.post("/projects", json={
        "name": "Project A",
        "jurisdiction_profile_id": seed_refs["jp_id"],
        "library_version_id": seed_refs["lv_id"],
    })

    clientB = _make_client(db, ORG2_CLAIMS)
    clientB.post("/me/org/provision", json={"name": "Org B"})
    r = clientB.get("/projects")
    assert r.status_code == 200
    assert r.json() == []

def test_list_projects_returns_created(db, seed_refs):
    client = _make_client(db, ORG_CLAIMS)
    client.post("/me/org/provision", json={"name": "Org A"})
    client.post("/projects", json={
        "name": "Project A",
        "jurisdiction_profile_id": seed_refs["jp_id"],
        "library_version_id": seed_refs["lv_id"],
    })
    r = client.get("/projects")
    assert len(r.json()) == 1
    assert r.json()[0]["name"] == "Project A"


# ── GET /projects/{id} ────────────────────────────────────────────────────────

def test_get_project(db, seed_refs):
    client = _make_client(db, ORG_CLAIMS)
    client.post("/me/org/provision", json={"name": "Org A"})
    created = client.post("/projects", json={
        "name": "Project A",
        "jurisdiction_profile_id": seed_refs["jp_id"],
        "library_version_id": seed_refs["lv_id"],
    }).json()
    r = client.get(f"/projects/{created['id']}")
    assert r.status_code == 200
    assert r.json()["id"] == created["id"]

def test_get_project_wrong_org_returns_404(db, seed_refs):
    clientA = _make_client(db, ORG_CLAIMS)
    clientA.post("/me/org/provision", json={"name": "Org A"})
    project = clientA.post("/projects", json={
        "name": "A's project",
        "jurisdiction_profile_id": seed_refs["jp_id"],
        "library_version_id": seed_refs["lv_id"],
    }).json()

    clientB = _make_client(db, ORG2_CLAIMS)
    clientB.post("/me/org/provision", json={"name": "Org B"})
    r = clientB.get(f"/projects/{project['id']}")
    assert r.status_code == 404


# ── POST /projects/{id}/pods ──────────────────────────────────────────────────

@pytest.fixture
def project_id(db, seed_refs):
    client = _make_client(db, ORG_CLAIMS)
    client.post("/me/org/provision", json={"name": "Org A"})
    r = client.post("/projects", json={
        "name": "Housing Project",
        "jurisdiction_profile_id": seed_refs["jp_id"],
        "library_version_id": seed_refs["lv_id"],
    })
    return r.json()["id"]

_STUDIO_BODY = {
    "name": "Studio 3x6",
    "width_m": 3.0,
    "length_m": 6.0,
    "wall_height_m": 2.7,
    "roof_type": "duo_pitch",
    "roof_pitch_deg": 15.0,
    "openings": [],
}

def test_create_pod_returns_201(db, project_id):
    client = _make_client(db, ORG_CLAIMS)
    r = client.post(f"/projects/{project_id}/pods", json=_STUDIO_BODY)
    assert r.status_code == 201

def test_create_pod_has_id_and_name(db, project_id):
    client = _make_client(db, ORG_CLAIMS)
    body = client.post(f"/projects/{project_id}/pods", json=_STUDIO_BODY).json()
    assert body["name"] == "Studio 3x6"
    assert "id" in body

def test_create_pod_returns_elements(db, project_id):
    client = _make_client(db, ORG_CLAIMS)
    body = client.post(f"/projects/{project_id}/pods", json=_STUDIO_BODY).json()
    assert len(body["elements"]) > 0

def test_create_pod_elements_have_types(db, project_id):
    client = _make_client(db, ORG_CLAIMS)
    body = client.post(f"/projects/{project_id}/pods", json=_STUDIO_BODY).json()
    types = {e["type"] for e in body["elements"]}
    assert "ExternalWall" in types
    assert "Floor" in types
    assert "Roof" in types

def test_create_pod_with_openings(db, project_id):
    client = _make_client(db, ORG_CLAIMS)
    payload = dict(_STUDIO_BODY)
    payload["openings"] = [
        {"wall": "S", "type": "door", "width_m": 0.9, "height_m": 2.1, "sill_height_m": 0.0}
    ]
    r = client.post(f"/projects/{project_id}/pods", json=payload)
    assert r.status_code == 201
    types = {e["type"] for e in r.json()["elements"]}
    assert "Opening" in types

def test_create_pod_geometry_stored(db, project_id):
    client = _make_client(db, ORG_CLAIMS)
    body = client.post(f"/projects/{project_id}/pods", json=_STUDIO_BODY).json()
    g = body["geometry_2d"]
    assert g["width_m"] == 3.0
    assert g["length_m"] == 6.0

def test_create_pod_wrong_project_returns_404(db, seed_refs):
    clientA = _make_client(db, ORG_CLAIMS)
    clientA.post("/me/org/provision", json={"name": "Org A"})
    project = clientA.post("/projects", json={
        "name": "A project",
        "jurisdiction_profile_id": seed_refs["jp_id"],
        "library_version_id": seed_refs["lv_id"],
    }).json()

    clientB = _make_client(db, ORG2_CLAIMS)
    clientB.post("/me/org/provision", json={"name": "Org B"})
    r = clientB.post(f"/projects/{project['id']}/pods", json=_STUDIO_BODY)
    assert r.status_code == 404


# ── GET /projects/{id}/pods ───────────────────────────────────────────────────

def test_list_pods_empty(db, project_id):
    client = _make_client(db, ORG_CLAIMS)
    r = client.get(f"/projects/{project_id}/pods")
    assert r.status_code == 200
    assert r.json() == []

def test_list_pods_returns_created(db, project_id):
    client = _make_client(db, ORG_CLAIMS)
    client.post(f"/projects/{project_id}/pods", json=_STUDIO_BODY)
    r = client.get(f"/projects/{project_id}/pods")
    assert len(r.json()) == 1
    assert r.json()[0]["name"] == "Studio 3x6"


# ── GET /projects/{id}/pods/{pod_id} ─────────────────────────────────────────

def test_get_pod_returns_elements(db, project_id):
    client = _make_client(db, ORG_CLAIMS)
    created = client.post(f"/projects/{project_id}/pods", json=_STUDIO_BODY).json()
    r = client.get(f"/projects/{project_id}/pods/{created['id']}")
    assert r.status_code == 200
    assert len(r.json()["elements"]) > 0

def test_get_pod_not_found(db, project_id):
    client = _make_client(db, ORG_CLAIMS)
    r = client.get(f"/projects/{project_id}/pods/{uuid.uuid4()}")
    assert r.status_code == 404
