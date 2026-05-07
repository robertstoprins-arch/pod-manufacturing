"""
Integration tests for material price endpoints.

GET    /materials/{id}/prices
POST   /materials/{id}/prices
PUT    /material-prices/{price_id}
DELETE /material-prices/{price_id}
POST   /material-prices/{price_id}/set-default
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db import get_db
from app.models import LibraryVersion, MaterialLibrary, MaterialPrice


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
    lv = LibraryVersion(version="v1.0-prices-test")
    db.add(lv)
    db.commit()
    db.refresh(lv)
    return lv


@pytest.fixture
def mat(db, lv):
    m = MaterialLibrary(
        library_version_id=lv.id,
        name="OSB 18mm",
        lambda_W_mK=0.13,
        supplier_ref="TEST-OSB",
        unit="m2",
        currency="EUR",
    )
    db.add(m)
    db.commit()
    db.refresh(m)
    return m


@pytest.fixture
def mat2(db, lv):
    m = MaterialLibrary(
        library_version_id=lv.id,
        name="C24 Timber 140mm",
        lambda_W_mK=0.13,
        supplier_ref="TEST-C24",
        unit="lm",
        currency="EUR",
    )
    db.add(m)
    db.commit()
    db.refresh(m)
    return m


# ── GET /materials/{id}/prices ────────────────────────────────────────────────

def test_list_prices_empty(db, mat):
    client = _make_client(db)
    r = client.get(f"/materials/{mat.id}/prices")
    assert r.status_code == 200
    assert r.json() == []


def test_list_prices_404_for_unknown_material(db):
    client = _make_client(db)
    r = client.get("/materials/99999/prices")
    assert r.status_code == 404


def test_list_prices_returns_all(db, mat):
    db.add(MaterialPrice(material_id=mat.id, price_type="retail_lv",
                         price_per_unit=12.50, unit="m2", currency="EUR"))
    db.add(MaterialPrice(material_id=mat.id, price_type="trade_lv",
                         price_per_unit=10.00, unit="m2", currency="EUR"))
    db.commit()
    client = _make_client(db)
    r = client.get(f"/materials/{mat.id}/prices")
    assert r.status_code == 200
    assert len(r.json()) == 2


# ── POST /materials/{id}/prices ───────────────────────────────────────────────

def test_add_price_returns_201(db, mat):
    client = _make_client(db)
    r = client.post(f"/materials/{mat.id}/prices", json={
        "price_type": "retail_lv",
        "price_per_unit": 15.00,
        "unit": "m2",
        "currency": "EUR",
    })
    assert r.status_code == 201
    body = r.json()
    assert body["price_per_unit"] == 15.00
    assert body["price_type"] == "retail_lv"
    assert body["unit"] == "m2"
    assert body["is_default"] is False
    assert body["material_id"] == mat.id


def test_add_price_404_for_unknown_material(db):
    client = _make_client(db)
    r = client.post("/materials/99999/prices", json={
        "price_type": "retail_lv", "price_per_unit": 5.0, "unit": "m2",
    })
    assert r.status_code == 404


def test_add_price_invalid_price_type(db, mat):
    client = _make_client(db)
    r = client.post(f"/materials/{mat.id}/prices", json={
        "price_type": "made_up_type",
        "price_per_unit": 5.0,
        "unit": "m2",
    })
    assert r.status_code == 422


def test_add_price_invalid_unit(db, mat):
    client = _make_client(db)
    r = client.post(f"/materials/{mat.id}/prices", json={
        "price_type": "retail_lv",
        "price_per_unit": 5.0,
        "unit": "kg",
    })
    assert r.status_code == 422


def test_add_price_as_default_clears_existing_default(db, mat):
    """Setting is_default=True on a new price should clear the previous default."""
    db.add(MaterialPrice(material_id=mat.id, price_type="retail_lv",
                         price_per_unit=12.50, unit="m2", is_default=True))
    db.commit()

    client = _make_client(db)
    r = client.post(f"/materials/{mat.id}/prices", json={
        "price_type": "trade_lv",
        "price_per_unit": 10.00,
        "unit": "m2",
        "is_default": True,
    })
    assert r.status_code == 201

    prices = db.query(MaterialPrice).filter(MaterialPrice.material_id == mat.id).all()
    defaults = [p for p in prices if p.is_default]
    assert len(defaults) == 1
    assert defaults[0].price_type == "trade_lv"


def test_add_price_with_all_optional_fields(db, mat):
    client = _make_client(db)
    r = client.post(f"/materials/{mat.id}/prices", json={
        "price_type": "import_benchmark",
        "price_per_unit": 8.75,
        "unit": "m2",
        "currency": "GBP",
        "supplier_ref": "SUP-001",
        "notes": "Q1 2026 landed cost",
        "is_default": False,
    })
    assert r.status_code == 201
    body = r.json()
    assert body["currency"] == "GBP"
    assert body["supplier_ref"] == "SUP-001"
    assert body["notes"] == "Q1 2026 landed cost"


# ── PUT /material-prices/{price_id} ──────────────────────────────────────────

def test_update_price_partial(db, mat):
    p = MaterialPrice(material_id=mat.id, price_type="retail_lv",
                      price_per_unit=12.50, unit="m2", currency="EUR")
    db.add(p)
    db.commit()
    db.refresh(p)

    client = _make_client(db)
    r = client.put(f"/material-prices/{p.id}", json={"price_per_unit": 13.99})
    assert r.status_code == 200
    assert r.json()["price_per_unit"] == 13.99
    assert r.json()["price_type"] == "retail_lv"  # unchanged


def test_update_price_404(db):
    client = _make_client(db)
    r = client.put("/material-prices/99999", json={"price_per_unit": 5.0})
    assert r.status_code == 404


def test_update_price_invalid_price_type(db, mat):
    p = MaterialPrice(material_id=mat.id, price_type="retail_lv",
                      price_per_unit=12.50, unit="m2")
    db.add(p)
    db.commit()
    db.refresh(p)
    client = _make_client(db)
    r = client.put(f"/material-prices/{p.id}", json={"price_type": "not_valid"})
    assert r.status_code == 422


def test_update_price_set_default_clears_others(db, mat):
    p1 = MaterialPrice(material_id=mat.id, price_type="retail_lv",
                       price_per_unit=12.50, unit="m2", is_default=True)
    p2 = MaterialPrice(material_id=mat.id, price_type="trade_lv",
                       price_per_unit=10.00, unit="m2", is_default=False)
    db.add_all([p1, p2])
    db.commit()
    db.refresh(p1)
    db.refresh(p2)

    client = _make_client(db)
    r = client.put(f"/material-prices/{p2.id}", json={"is_default": True})
    assert r.status_code == 200

    db.expire_all()
    assert db.get(MaterialPrice, p1.id).is_default is False
    assert db.get(MaterialPrice, p2.id).is_default is True


# ── DELETE /material-prices/{price_id} ───────────────────────────────────────

def test_delete_price(db, mat):
    p = MaterialPrice(material_id=mat.id, price_type="retail_lv",
                      price_per_unit=12.50, unit="m2")
    db.add(p)
    db.commit()
    db.refresh(p)
    pid = p.id

    client = _make_client(db)
    r = client.delete(f"/material-prices/{pid}")
    assert r.status_code == 204
    assert db.get(MaterialPrice, pid) is None


def test_delete_price_404(db):
    client = _make_client(db)
    r = client.delete("/material-prices/99999")
    assert r.status_code == 404


# ── POST /material-prices/{price_id}/set-default ─────────────────────────────

def test_set_default_promotes_target(db, mat):
    p1 = MaterialPrice(material_id=mat.id, price_type="retail_lv",
                       price_per_unit=12.50, unit="m2", is_default=True)
    p2 = MaterialPrice(material_id=mat.id, price_type="trade_lv",
                       price_per_unit=10.00, unit="m2", is_default=False)
    db.add_all([p1, p2])
    db.commit()
    db.refresh(p1)
    db.refresh(p2)

    client = _make_client(db)
    r = client.post(f"/material-prices/{p2.id}/set-default")
    assert r.status_code == 200
    assert r.json()["is_default"] is True
    assert r.json()["id"] == p2.id

    db.expire_all()
    assert db.get(MaterialPrice, p1.id).is_default is False


def test_set_default_404(db):
    client = _make_client(db)
    r = client.post("/material-prices/99999/set-default")
    assert r.status_code == 404


def test_set_default_only_one_default_per_material(db, mat, mat2):
    """Clearing defaults must be scoped to the target material, not all materials."""
    p_mat1 = MaterialPrice(material_id=mat.id, price_type="retail_lv",
                            price_per_unit=12.50, unit="m2", is_default=True)
    p_mat2 = MaterialPrice(material_id=mat2.id, price_type="trade_lv",
                            price_per_unit=5.00, unit="lm", is_default=True)
    db.add_all([p_mat1, p_mat2])
    db.commit()
    db.refresh(p_mat1)
    db.refresh(p_mat2)

    # Adding a second default to mat1 should NOT affect mat2's default
    p_mat1_trade = MaterialPrice(material_id=mat.id, price_type="trade_lv",
                                  price_per_unit=10.00, unit="m2", is_default=False)
    db.add(p_mat1_trade)
    db.commit()
    db.refresh(p_mat1_trade)

    client = _make_client(db)
    r = client.post(f"/material-prices/{p_mat1_trade.id}/set-default")
    assert r.status_code == 200

    db.expire_all()
    # mat1's old default cleared
    assert db.get(MaterialPrice, p_mat1.id).is_default is False
    # mat2's default untouched
    assert db.get(MaterialPrice, p_mat2.id).is_default is True


# ── Cross-material isolation ──────────────────────────────────────────────────

def test_list_prices_isolated_per_material(db, mat, mat2):
    db.add(MaterialPrice(material_id=mat.id, price_type="retail_lv",
                         price_per_unit=12.50, unit="m2"))
    db.add(MaterialPrice(material_id=mat2.id, price_type="trade_lv",
                         price_per_unit=4.00, unit="lm"))
    db.commit()

    client = _make_client(db)
    r1 = client.get(f"/materials/{mat.id}/prices")
    r2 = client.get(f"/materials/{mat2.id}/prices")
    assert len(r1.json()) == 1
    assert len(r2.json()) == 1
    assert r1.json()[0]["unit"] == "m2"
    assert r2.json()[0]["unit"] == "lm"


# ── BOM safety — prices absence must not break material lookups ───────────────

def test_material_with_no_prices_still_listed(db, mat):
    """A material with zero prices must not cause 404 on list."""
    client = _make_client(db)
    r = client.get(f"/materials/{mat.id}/prices")
    assert r.status_code == 200
    assert r.json() == []
