"""
Skill: U-Value Pre-Check

Calculates the thermal transmittance (U-value) of a building element using the
isothermal planes method (ISO 6946:2017) and compares it against a jurisdiction
target. For bridged layers (e.g. timber studs + mineral wool fill), the parallel
path method is used to calculate an effective conductivity.

Pure function — no database access. Lambda values are embedded in the preset
build-ups or supplied directly by the caller.

Method
──────
  R_total = R_si + Σ R_layer + R_se
  U = 1 / R_total

  Bridged layer effective lambda (parallel path):
    λ_eff = f_frame × λ_frame + (1 − f_frame) × λ_fill

  Surface resistances per ISO 6946:2017 Table 1:
    ExternalWall : R_si = 0.13,  R_se = 0.04  (horizontal heat flow)
    Roof         : R_si = 0.10,  R_se = 0.04  (upward heat flow)
    Floor        : R_si = 0.17,  R_se = 0.04  (downward heat flow)
"""
from dataclasses import dataclass, field
from typing import Literal


ElementType = Literal["ExternalWall", "Floor", "Roof"]


@dataclass
class UValueLayer:
    """One layer in a thermal build-up."""
    name: str
    thickness_mm: float
    lambda_W_mK: float            # conductivity of fill or continuous material
    framing_fraction: float = 0.0 # fraction of cross-section that is structural framing
    lambda_framing: float = 0.13  # conductivity of framing material (KVH C24 default)


@dataclass
class LayerResult:
    name: str
    thickness_mm: float
    lambda_effective: float       # after bridging adjustment
    r_value: float                # m²K/W


@dataclass
class UValueResult:
    element_type: str
    element_label: str
    u_value: float                # W/m²K
    r_total: float                # m²K/W
    r_si: float
    r_se: float
    layers: list[LayerResult]
    target_u: float
    status: str                   # "PASS" or "FAIL"
    margin: float                 # target_u - u_value (positive = headroom)


class UValueError(ValueError):
    pass


# ISO 6946:2017 Table 1 surface resistances (R_si, R_se) in m²K/W
_SURFACE_R: dict[str, tuple[float, float]] = {
    "ExternalWall": (0.13, 0.04),
    "Roof":         (0.10, 0.04),
    "Floor":        (0.17, 0.04),
}

# Jurisdiction thermal targets (W/m²K) — mirrors the seeded JurisdictionProfile rows
JURISDICTION_TARGETS: dict[str, dict[str, float]] = {
    "BBR_SE": {
        "ExternalWall": 0.18,
        "Roof":         0.13,
        "Floor":        0.15,
        "window":       1.20,
    },
    "TEK17_NO": {
        "ExternalWall": 0.18,
        "Roof":         0.13,
        "Floor":        0.10,
        "window":       0.80,
    },
}


def _validate(element_type: str, layers: list[UValueLayer], target_u: float) -> None:
    if element_type not in _SURFACE_R:
        raise UValueError(
            f"Unknown element_type {element_type!r}. "
            f"Expected one of: {list(_SURFACE_R)}"
        )
    if target_u <= 0:
        raise UValueError("target_u must be positive.")
    if not layers:
        raise UValueError("layers list is empty — cannot calculate U-value.")
    for layer in layers:
        if layer.thickness_mm <= 0:
            raise UValueError(f"Layer '{layer.name}': thickness_mm must be > 0.")
        if layer.lambda_W_mK <= 0:
            raise UValueError(f"Layer '{layer.name}': lambda_W_mK must be > 0.")
        if not (0.0 <= layer.framing_fraction < 1.0):
            raise UValueError(
                f"Layer '{layer.name}': framing_fraction must be in [0, 1)."
            )
        if layer.framing_fraction > 0 and layer.lambda_framing <= 0:
            raise UValueError(
                f"Layer '{layer.name}': lambda_framing must be > 0 when framing_fraction > 0."
            )


def calculate_u_value(
    element_type: ElementType,
    layers: list[UValueLayer],
    target_u: float,
    element_label: str = "",
) -> UValueResult:
    """
    Calculate the U-value of a building element and check it against a target.

    Parameters
    ----------
    element_type   "ExternalWall", "Floor", or "Roof"
    layers         Layer sequence from outside to inside (or inside to outside —
                   direction doesn't affect the result)
    target_u       Jurisdiction limit in W/m²K
    element_label  Optional label for output (e.g. "wall_N")

    Returns
    -------
    UValueResult with status "PASS" or "FAIL" and per-layer breakdown.
    """
    _validate(element_type, layers, target_u)

    r_si, r_se = _SURFACE_R[element_type]
    layer_results: list[LayerResult] = []

    for layer in layers:
        if layer.framing_fraction > 0:
            # Parallel path method for bridged layer (stud + insulation fill)
            lambda_eff = (
                layer.framing_fraction * layer.lambda_framing
                + (1.0 - layer.framing_fraction) * layer.lambda_W_mK
            )
        else:
            lambda_eff = layer.lambda_W_mK

        r = (layer.thickness_mm / 1000.0) / lambda_eff
        layer_results.append(LayerResult(
            name=layer.name,
            thickness_mm=layer.thickness_mm,
            lambda_effective=round(lambda_eff, 6),
            r_value=round(r, 4),
        ))

    r_total = r_si + sum(lr.r_value for lr in layer_results) + r_se
    u_value = 1.0 / r_total

    return UValueResult(
        element_type=element_type,
        element_label=element_label,
        u_value=round(u_value, 4),
        r_total=round(r_total, 4),
        r_si=r_si,
        r_se=r_se,
        layers=layer_results,
        target_u=target_u,
        status="PASS" if u_value <= target_u else "FAIL",
        margin=round(target_u - u_value, 4),
    )


# ── Default Nordic closed-panel thermal build-ups ─────────────────────────────
# Lambda values sourced from materials_template.xlsx.
# Bridged layers represent the structural framing zone (studs/joists/rafters)
# with mineral wool fill, using the parallel path method.
#
# These build-ups will FAIL BBR/TEK17 targets out of the box — they represent
# the baseline 47×147/195 stud wall and should be used to demonstrate the gap
# between a simple stud wall and a compliant build-up.

NORDIC_WALL_THERMAL = [
    # Inside → outside
    UValueLayer("Gyproc Standard 12.5mm",         thickness_mm=12.5,  lambda_W_mK=0.250),
    UValueLayer("Siga Majrex 200 VCL",            thickness_mm=0.2,   lambda_W_mK=0.170),
    UValueLayer("Stud zone: KVH 47×147 + Rockwool",
                thickness_mm=147.0, lambda_W_mK=0.037,
                framing_fraction=round(47 / 600, 5), lambda_framing=0.13),
    UValueLayer("OSB/3 12mm",                     thickness_mm=12.0,  lambda_W_mK=0.130),
    UValueLayer("Tyvek Housewrap Breather",       thickness_mm=0.5,   lambda_W_mK=0.170),
    UValueLayer("Latvian Spruce Cladding 21mm",   thickness_mm=21.0,  lambda_W_mK=0.130),
]

NORDIC_FLOOR_THERMAL = [
    UValueLayer("OSB/3 18mm deck",                thickness_mm=18.0,  lambda_W_mK=0.130),
    UValueLayer("Joist zone: KVH 47×195 + Rockwool",
                thickness_mm=195.0, lambda_W_mK=0.037,
                framing_fraction=round(47 / 400, 5), lambda_framing=0.13),
    UValueLayer("Siga Majrex 200 VCL",            thickness_mm=0.2,   lambda_W_mK=0.170),
]

NORDIC_ROOF_THERMAL = [
    UValueLayer("OSB/3 12mm deck",                thickness_mm=12.0,  lambda_W_mK=0.130),
    UValueLayer("Rafter zone: KVH 47×195 + Paroc",
                thickness_mm=195.0, lambda_W_mK=0.033,
                framing_fraction=round(47 / 600, 5), lambda_framing=0.13),
    UValueLayer("Siga Majrex 200 VCL",            thickness_mm=0.2,   lambda_W_mK=0.170),
    UValueLayer("Gyproc Standard 12.5mm",         thickness_mm=12.5,  lambda_W_mK=0.250),
]

# Preset map used by the API
THERMAL_PRESETS: dict[str, dict[str, list[UValueLayer]]] = {
    "nordic_standard": {
        "ExternalWall": NORDIC_WALL_THERMAL,
        "Floor":        NORDIC_FLOOR_THERMAL,
        "Roof":         NORDIC_ROOF_THERMAL,
    },
}
