"""
Tests for the standard_build_ups seed script.

Verifies: idempotency, correct count, and U-value results for key templates.
"""
import pytest
from sqlalchemy.orm import Session

from app.models import BuildUp, BuildUpLayer, LibraryVersion, MaterialLibrary
from app.skills.build_up_resolver import ResolverLayer, resolve
from seeds.standard_build_ups import seed
from seeds.standard_materials import MATERIALS


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def lv(db):
    lv = LibraryVersion(version="v1.0-seed-test")
    db.add(lv)
    db.commit()
    db.refresh(lv)
    return lv


@pytest.fixture
def full_materials(db, lv):
    """Seed all 14 standard materials needed by the build-up seed."""
    for m in MATERIALS:
        db.add(MaterialLibrary(library_version_id=lv.id, **m))
    db.commit()


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_seed_creates_10_templates(db, full_materials):
    seeded, skipped = seed(db)
    db.commit()
    assert seeded == 10
    assert skipped == 0
    assert db.query(BuildUp).count() == 10


def test_seed_is_idempotent(db, full_materials):
    seed(db)
    db.commit()

    seeded2, skipped2 = seed(db)
    db.commit()

    assert seeded2 == 0
    assert skipped2 == 10
    assert db.query(BuildUp).count() == 10


def test_standard_wall_u_value_passes_bbr_tek17(db, full_materials):
    seed(db)
    db.commit()

    bu = db.query(BuildUp).filter_by(name="Nordic Standard Wall — Closed Panel").first()
    assert bu is not None

    resolver_layers = _bu_to_resolver_layers(db, bu)
    result = resolve(resolver_layers, "ExternalWall")

    assert result.u_value > 0, "U-value should be computed"
    assert result.u_value <= 0.18, f"Expected U ≤ 0.18 (BBR/TEK17), got {result.u_value:.3f}"


def test_light_wall_u_value_fails_habitable_target(db, full_materials):
    seed(db)
    db.commit()

    bu = db.query(BuildUp).filter_by(name="Light Wall — Garden / Storage").first()
    assert bu is not None

    resolver_layers = _bu_to_resolver_layers(db, bu)
    result = resolve(resolver_layers, "ExternalWall")

    assert result.u_value > 0.25, (
        f"Light wall should have U > 0.25 (non-habitable target), got {result.u_value:.3f}"
    )


# ── Helper ────────────────────────────────────────────────────────────────────

def _bu_to_resolver_layers(db: Session, bu: BuildUp) -> list[ResolverLayer]:
    out = []
    for layer in sorted(bu.layers, key=lambda l: l.position_order):
        mat = db.get(MaterialLibrary, layer.material_id)
        props = layer.properties or {}
        out.append(ResolverLayer(
            name=mat.name,
            thickness_mm=layer.thickness_mm,
            lambda_W_mK=mat.lambda_W_mK,
            role=props.get("role", ""),
            framing_fraction=props.get("framing_fraction", 0.0),
            include_in_u_value=props.get("include_in_u_value", True),
            sd_value_m=props.get("sd_value_m"),
        ))
    return out
