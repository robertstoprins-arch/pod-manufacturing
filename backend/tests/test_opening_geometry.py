"""Tests for opening geometry: x_offset_m, shape, and bounds validation."""
import pytest
from app.skills.element_decomposer import DecompositionError, OpeningSpec, decompose_pod


def _openings(elements, wall: str):
    return [e for e in elements if e.type == "Opening" and e.geometry["wall"] == wall]


def _pod(openings):
    return decompose_pod(width_m=3.0, length_m=6.0, wall_height_m=2.7, openings=openings)


# ── Rectangular ───────────────────────────────────────────────────────────────

def test_rectangular_x_offset_1500():
    o = OpeningSpec(wall="S", type="window", width_m=1.2, height_m=1.1,
                    sill_height_m=0.9, x_offset_m=1.5, shape="rectangular")
    (e,) = _openings(_pod([o]), "S")
    assert e.geometry["x_offset_m"] == 1.5
    assert e.geometry["shape"] == "rectangular"


def test_rectangular_x_offset_zero():
    """Zero offset must be stored as 0, not treated as 'no offset'."""
    o = OpeningSpec(wall="S", type="window", width_m=1.2, height_m=1.1,
                    sill_height_m=0.9, x_offset_m=0.0, shape="rectangular")
    (e,) = _openings(_pod([o]), "S")
    assert e.geometry["x_offset_m"] == 0.0


# ── Circular ──────────────────────────────────────────────────────────────────

def test_circular_x_offset_1500():
    """Left tangent at 1.5 m → right tangent at 1.5 + 0.8 = 2.3 m."""
    o = OpeningSpec(wall="S", type="vent", width_m=0.8, height_m=0.8,
                    sill_height_m=1.1, x_offset_m=1.5, shape="circular")
    (e,) = _openings(_pod([o]), "S")
    g = e.geometry
    assert g["shape"] == "circular"
    assert g["x_offset_m"] == 1.5
    assert abs(g["x_offset_m"] + g["width_m"] - 2.3) < 0.001


def test_circular_x_offset_zero():
    """Zero offset for circular: left tangent at wall start."""
    o = OpeningSpec(wall="E", type="vent", width_m=0.6, height_m=0.6,
                    sill_height_m=1.0, x_offset_m=0.0, shape="circular")
    (e,) = _openings(_pod([o]), "E")
    assert e.geometry["x_offset_m"] == 0.0


# ── Bounds validation ─────────────────────────────────────────────────────────

def test_circular_exceeds_wall_boundary():
    """Circular opening whose right tangent exceeds wall span must be rejected."""
    # E wall spans width_m = 3.0 m; x=2.8 + diameter=0.8 → right=3.6 m → invalid
    o = OpeningSpec(wall="E", type="vent", width_m=0.8, height_m=0.8,
                    sill_height_m=1.0, x_offset_m=2.8, shape="circular")
    with pytest.raises(DecompositionError, match="exceeds wall span"):
        _pod([o])
