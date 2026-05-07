"""
Integration tests for /materials and /build-ups endpoints.

Uses SQLite in-memory fixture from conftest. Auth is not required
on these endpoints — they are public library endpoints.
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db import get_db
from app.models import LibraryVersion, MaterialLibrary


# ── Client factory ────────────────────────────────────────────────────────────

def _make_client(db_session) -> TestClient:
    app.dependency_overrides[get_db] = lambda: db_session
    return TestClient(app, raise_server_exceptions=True)


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.clear()


# ── Seed helpers ──────────────────────────────────────────────────────────────

@pytest.fixture
def lv(db):
    lv = LibraryVersion(version="v1.0-test")
    db.add(lv)
    db.commit()
    db.refresh(lv)
    return lv


@pytest.fixture
def materials(db, lv):
    """Seed minimal materials for layer tests."""
    mats = [
        MaterialLibrary(
            library_version_id=lv.id, name="Plasterboard 12.5mm",
            lambda_W_mK=0.25, supplier_ref="TEST-PB",
            properties={"default_role": "internal_finish", "include_in_u_value": True},
        ),
        MaterialLibrary(
            library_version_id=lv.id, name="VCL membrane",
            lambda_W_mK=0.17, supplier_ref="TEST-VCL",
            properties={"default_role": "vcl", "include_in_u_value": False},
        ),
        MaterialLibrary(
            library_version_id=lv.id, name="PIR insulation 140mm",
            lambda_W_mK=0.023, supplier_ref="TEST-PIR-140",
            properties={"default_role": "framing_zone", "include_in_u_value": True},
        ),
        MaterialLibrary(
            library_version_id=lv.id, name="Breather membrane",
            lambda_W_mK=0.17, supplier_ref="TEST-BREATHER",
            properties={"default_role": "breather", "include_in_u_value": False},
        ),
        MaterialLibrary(
            library_version_id=lv.id, name="FC Cladding 12mm",
            lambda_W_mK=0.35, supplier_ref="TEST-CLAD",
            properties={"default_role": "cladding", "include_in_u_value": True},
        ),
    ]
    db.add_all(mats)
    db.commit()
    for m in mats:
        db.refresh(m)
    return mats


def _material_ids(materials):
    return {m.supplier_ref: m.id for m in materials}


def _nordic_layers(mids):
    """Return a valid Nordic wall layer payload (inside → outside, 5 layers)."""
    return [
        {"material_id": mids["TEST-PB"],      "thickness_mm": 12.5,  "position_order": 1,
         "role": "internal_finish", "framing_fraction": 0.0, "include_in_u_value": True},
        {"material_id": mids["TEST-VCL"],     "thickness_mm": 0.2,   "position_order": 2,
         "role": "vcl", "framing_fraction": 0.0, "include_in_u_value": False},
        {"material_id": mids["TEST-PIR-140"], "thickness_mm": 140.0, "position_order": 3,
         "role": "framing_zone", "framing_fraction": 0.15, "include_in_u_value": True},
        {"material_id": mids["TEST-BREATHER"],"thickness_mm": 0.2,   "position_order": 4,
         "role": "breather", "framing_fraction": 0.0, "include_in_u_value": False},
        {"material_id": mids["TEST-CLAD"],    "thickness_mm": 12.0,  "position_order": 5,
         "role": "cladding", "framing_fraction": 0.0, "include_in_u_value": True},
    ]


# ── GET /materials ────────────────────────────────────────────────────────────

def test_list_materials_empty(db):
    client = _make_client(db)
    r = client.get("/materials")
    assert r.status_code == 200
    assert r.json() == []


def test_list_materials_returns_seeded(db, materials):
    client = _make_client(db)
    r = client.get("/materials")
    assert r.status_code == 200
    assert len(r.json()) == len(materials)


def test_get_material_by_id(db, materials):
    client = _make_client(db)
    mat_id = materials[0].id
    r = client.get(f"/materials/{mat_id}")
    assert r.status_code == 200
    assert r.json()["id"] == mat_id
    assert r.json()["lambda_W_mK"] == materials[0].lambda_W_mK


def test_get_material_not_found(db):
    client = _make_client(db)
    r = client.get("/materials/99999")
    assert r.status_code == 404


# ── POST /build-ups/validate ──────────────────────────────────────────────────

def test_validate_returns_u_value(db, materials):
    client = _make_client(db)
    mids = _material_ids(materials)
    r = client.post("/build-ups/validate", json={
        "element_type": "ExternalWall",
        "layers": _nordic_layers(mids),
    })
    assert r.status_code == 200
    body = r.json()
    assert body["u_value"] > 0
    assert isinstance(body["errors"], list)
    assert isinstance(body["warnings"], list)
    assert isinstance(body["targets"], list)
    assert isinstance(body["assumptions"], list)


def test_validate_returns_errors_without_save(db, materials):
    client = _make_client(db)
    mids = _material_ids(materials)
    # Layer with zero thickness should trigger an error
    bad_layers = [
        {"material_id": mids["TEST-PB"], "thickness_mm": 0.0, "position_order": 1,
         "role": "internal_finish", "framing_fraction": 0.0, "include_in_u_value": True},
        {"material_id": mids["TEST-PIR-140"], "thickness_mm": 140.0, "position_order": 2,
         "role": "insulation", "framing_fraction": 0.0, "include_in_u_value": True},
    ]
    r = client.post("/build-ups/validate", json={
        "element_type": "ExternalWall",
        "layers": bad_layers,
    })
    assert r.status_code == 200
    assert len(r.json()["errors"]) > 0
    # Validate does NOT persist — list of build-ups should be empty
    r2 = client.get("/build-ups")
    assert r2.status_code == 200
    assert r2.json() == []


def test_validate_missing_vcl_returns_error(db, materials):
    client = _make_client(db)
    mids = _material_ids(materials)
    # No VCL layer
    layers_no_vcl = [
        {"material_id": mids["TEST-PB"],      "thickness_mm": 12.5,  "position_order": 1,
         "role": "internal_finish", "framing_fraction": 0.0, "include_in_u_value": True},
        {"material_id": mids["TEST-PIR-140"], "thickness_mm": 140.0, "position_order": 2,
         "role": "framing_zone", "framing_fraction": 0.15, "include_in_u_value": True},
        {"material_id": mids["TEST-CLAD"],    "thickness_mm": 12.0,  "position_order": 3,
         "role": "cladding", "framing_fraction": 0.0, "include_in_u_value": True},
    ]
    r = client.post("/build-ups/validate", json={
        "element_type": "ExternalWall",
        "layers": layers_no_vcl,
    })
    assert r.status_code == 200
    errors = r.json()["errors"]
    assert any("vcl" in e.lower() or "airtight" in e.lower() or "vapour control" in e.lower()
               for e in errors)


# ── POST /build-ups ───────────────────────────────────────────────────────────

def test_create_build_up(db, materials):
    client = _make_client(db)
    mids = _material_ids(materials)
    r = client.post("/build-ups", json={
        "name": "Test Nordic Wall",
        "element_type": "ExternalWall",
        "build_up_type": "closed_panel",
        "scope": "library",
        "status": "draft",
        "layers": _nordic_layers(mids),
    })
    assert r.status_code == 201
    body = r.json()
    assert body["id"] is not None
    assert body["name"] == "Test Nordic Wall"
    assert body["u_value"] > 0
    assert len(body["layers"]) == 5


def test_create_build_up_layers_ordered(db, materials):
    client = _make_client(db)
    mids = _material_ids(materials)
    r = client.post("/build-ups", json={
        "name": "Order Test",
        "element_type": "ExternalWall",
        "layers": _nordic_layers(mids),
    })
    layers = r.json()["layers"]
    orders = [l["position_order"] for l in layers]
    assert orders == sorted(orders), "Layers should be returned in position_order order"


# ── GET /build-ups ────────────────────────────────────────────────────────────

def test_list_build_ups_empty(db):
    client = _make_client(db)
    r = client.get("/build-ups")
    assert r.status_code == 200
    assert r.json() == []


def test_list_build_ups_returns_created(db, materials):
    client = _make_client(db)
    mids = _material_ids(materials)
    client.post("/build-ups", json={
        "name": "Wall A",
        "element_type": "ExternalWall",
        "layers": _nordic_layers(mids),
    })
    r = client.get("/build-ups")
    assert r.status_code == 200
    assert len(r.json()) == 1
    assert r.json()[0]["name"] == "Wall A"


# ── GET /build-ups/{id} ───────────────────────────────────────────────────────

def test_get_build_up_by_id(db, materials):
    client = _make_client(db)
    mids = _material_ids(materials)
    created = client.post("/build-ups", json={
        "name": "Named Wall",
        "element_type": "ExternalWall",
        "layers": _nordic_layers(mids),
    }).json()
    r = client.get(f"/build-ups/{created['id']}")
    assert r.status_code == 200
    assert r.json()["id"] == created["id"]
    assert r.json()["u_value"] > 0


def test_get_build_up_not_found(db):
    client = _make_client(db)
    r = client.get("/build-ups/99999")
    assert r.status_code == 404


# ── PUT /build-ups/{id} ───────────────────────────────────────────────────────

def test_update_build_up_replaces_layers(db, materials):
    client = _make_client(db)
    mids = _material_ids(materials)
    created = client.post("/build-ups", json={
        "name": "Original",
        "element_type": "ExternalWall",
        "layers": _nordic_layers(mids),
    }).json()
    bu_id = created["id"]

    # Update with a different name and fewer layers
    updated_layers = [
        {"material_id": mids["TEST-PB"],      "thickness_mm": 12.5,  "position_order": 1,
         "role": "internal_finish", "framing_fraction": 0.0, "include_in_u_value": True},
        {"material_id": mids["TEST-VCL"],     "thickness_mm": 0.2,   "position_order": 2,
         "role": "vcl", "framing_fraction": 0.0, "include_in_u_value": False},
        {"material_id": mids["TEST-PIR-140"], "thickness_mm": 200.0, "position_order": 3,
         "role": "insulation", "framing_fraction": 0.0, "include_in_u_value": True},
        {"material_id": mids["TEST-CLAD"],    "thickness_mm": 12.0,  "position_order": 4,
         "role": "cladding", "framing_fraction": 0.0, "include_in_u_value": True},
    ]
    r = client.put(f"/build-ups/{bu_id}", json={
        "name": "Updated Wall",
        "element_type": "ExternalWall",
        "layers": updated_layers,
    })
    assert r.status_code == 200
    body = r.json()
    assert body["name"] == "Updated Wall"
    assert len(body["layers"]) == 4


def test_update_build_up_not_found(db):
    client = _make_client(db)
    r = client.put("/build-ups/99999", json={
        "name": "Ghost",
        "element_type": "ExternalWall",
        "layers": [],
    })
    assert r.status_code == 404


# ── DELETE /build-ups/{id} ────────────────────────────────────────────────────

def test_delete_build_up(db, materials):
    """Draft project-scoped build-ups can be deleted."""
    client = _make_client(db)
    mids = _material_ids(materials)
    created = client.post("/build-ups", json={
        "name": "To Delete",
        "element_type": "ExternalWall",
        "scope": "project",
        "status": "draft",
        "layers": _nordic_layers(mids),
    }).json()
    bu_id = created["id"]

    r = client.delete(f"/build-ups/{bu_id}")
    assert r.status_code == 204

    r2 = client.get(f"/build-ups/{bu_id}")
    assert r2.status_code == 404


def test_delete_approved_library_build_up_blocked(db, materials):
    """Approved library templates must not be deletable — 403 with clear message."""
    client = _make_client(db)
    mids = _material_ids(materials)
    created = client.post("/build-ups", json={
        "name": "Library Standard Wall",
        "element_type": "ExternalWall",
        "scope": "library",
        "status": "approved",
        "layers": _nordic_layers(mids),
    }).json()
    bu_id = created["id"]

    r = client.delete(f"/build-ups/{bu_id}")
    assert r.status_code == 403
    assert "cannot be deleted" in r.json()["detail"]


def test_delete_nonexistent_build_up(db):
    client = _make_client(db)
    r = client.delete("/build-ups/99999")
    assert r.status_code == 404


# ── Response structure ────────────────────────────────────────────────────────

def test_response_includes_all_required_fields(db, materials):
    client = _make_client(db)
    mids = _material_ids(materials)
    r = client.post("/build-ups", json={
        "name": "Full Response Test",
        "element_type": "ExternalWall",
        "layers": _nordic_layers(mids),
    })
    body = r.json()
    for field in ("id", "name", "element_type", "layers", "u_value", "r_total",
                  "layer_results", "errors", "warnings", "targets", "assumptions"):
        assert field in body, f"Missing field: {field}"


def test_targets_are_preliminary(db, materials):
    client = _make_client(db)
    mids = _material_ids(materials)
    r = client.post("/build-ups", json={
        "name": "Target Label Test",
        "element_type": "ExternalWall",
        "layers": _nordic_layers(mids),
    })
    for target in r.json()["targets"]:
        label = target["label"].lower()
        assert "preliminary" in label or "profile" in label, \
            f"Target label should be preliminary/profile, got: {target['label']!r}"
