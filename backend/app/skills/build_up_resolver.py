"""
Skill: Build-Up Resolver

Pure function — no database access.

Takes an ordered list of building element layers (INSIDE → OUTSIDE,
position_order 1 = innermost) and returns a U-value result plus validation
errors, warnings, jurisdiction target checks, and calculation assumptions.

Reuses calculate_u_value() from u_value.py — no duplication.

Method
──────
  Layers with include_in_u_value=False (membranes, cavities) are excluded
  from the thermal resistance path but are still checked by validators.

  Framing zones: λ_eff = f × λ_frame + (1−f) × λ_fill  (parallel path)
"""
from dataclasses import dataclass, field
from typing import Literal

from app.skills.u_value import calculate_u_value, UValueLayer, LayerResult


ElementType = Literal["ExternalWall", "Floor", "Roof"]

_VCL_ROLES        = {"vcl", "airtight_layer"}
_INSULATION_ROLES = {"insulation", "framing_zone"}
_BREATHER_ROLES   = {"breather"}
_CLADDING_ROLES   = {"cladding", "external_finish"}

# Preliminary targets (W/m²K) — mirrors JurisdictionProfile seeded rows.
# Structure as TargetResult for future wiring to DB-persisted profiles.
_TARGETS: dict[str, dict[str, float]] = {
    "BBR":   {"ExternalWall": 0.18, "Roof": 0.13, "Floor": 0.15},
    "TEK17": {"ExternalWall": 0.18, "Roof": 0.13, "Floor": 0.10},
}


@dataclass
class ResolverLayer:
    """One layer in a build-up, ordered INSIDE → OUTSIDE."""
    name: str
    thickness_mm: float
    lambda_W_mK: float
    role: str = ""                        # see ROLES enum
    framing_fraction: float = 0.0         # fraction of cross-section that is structural framing
    lambda_framing: float = 0.13          # C24 timber default
    include_in_u_value: bool = True       # False for membranes, cavities — excluded from R path
    sd_value_m: float | None = None       # vapour diffusion resistance (informational)
    infill_lambda_W_mK: float | None = None  # composite framing zone: explicit infill lambda


@dataclass
class TargetResult:
    code: str               # "BBR" | "TEK17"
    element_type: str
    target_u_value: float
    passes: bool
    headroom: float         # target − actual (positive = margin)
    label: str = ""         # "BBR profile target" etc.


@dataclass
class ResolverResult:
    u_value: float
    r_total: float
    total_thickness_mm: float   # sum of ALL layer thicknesses (incl. non-thermal)
    layers: list                # list[LayerResult] from u_value.py; empty if calc failed
    errors: list[str]           # blocking — prevent save
    warnings: list[str]         # non-blocking
    targets: list[TargetResult]
    assumptions: list[str]


def resolve(layers: list[ResolverLayer], element_type: str) -> ResolverResult:
    """
    Validate a build-up and calculate its U-value.

    Parameters
    ----------
    layers        Ordered INSIDE → OUTSIDE (position 1 = innermost warm layer).
    element_type  "ExternalWall" | "Floor" | "Roof"

    Returns
    -------
    ResolverResult with computed U-value, errors, warnings, target checks,
    and assumptions. errors being non-empty indicates the build-up should
    not be saved without correction.
    """
    errors: list[str] = []
    warnings: list[str] = []

    # ── Structural validation ────────────────────────────────────────────────
    if len(layers) < 2:
        errors.append("Minimum 2 layers required.")

    for i, layer in enumerate(layers):
        if layer.thickness_mm <= 0:
            errors.append(
                f"Layer {i + 1} '{layer.name}': thickness must be > 0."
            )
        if layer.include_in_u_value and layer.lambda_W_mK <= 0:
            errors.append(
                f"Layer {i + 1} '{layer.name}': lambda (λ) must be > 0 for thermal layers."
            )
        if not (0.0 <= layer.framing_fraction < 1.0):
            errors.append(
                f"Layer {i + 1} '{layer.name}': framing_fraction must be in [0, 1)."
            )

    # ── VCL / airtight layer checks ──────────────────────────────────────────
    vcl_indices        = [i for i, l in enumerate(layers) if l.role in _VCL_ROLES]
    insulation_indices = [i for i, l in enumerate(layers) if l.role in _INSULATION_ROLES]

    if element_type == "ExternalWall":
        if not vcl_indices:
            errors.append("No VCL / airtight vapour control layer defined.")
        elif insulation_indices:
            first_ins_idx = min(insulation_indices)
            cold_side_vcls = [idx for idx in vcl_indices if idx > first_ins_idx]
            if cold_side_vcls:
                errors.append(
                    "VCL is on the cold side of the main insulation zone. "
                    "Move the VCL to the warm/inner side "
                    "(lower layer number in inside → outside order)."
                )

    # Vapour-tight layer outboard of insulation zone (separate from VCL wrong-side)
    if insulation_indices and vcl_indices:
        last_ins_idx = max(insulation_indices)
        outboard_vcls = [idx for idx in vcl_indices if idx > last_ins_idx]
        if outboard_vcls and element_type == "ExternalWall":
            # Only add if not already reported above (cold-side vcl already caught)
            pass  # already reported as "cold side" error above

    # ── Breather checks ──────────────────────────────────────────────────────
    breather_indices = [i for i, l in enumerate(layers) if l.role in _BREATHER_ROLES]
    if element_type == "ExternalWall":
        if not breather_indices:
            warnings.append(
                "No breather membrane found. "
                "Consider adding one outboard of the insulation zone."
            )
        elif insulation_indices:
            last_ins_idx = max(insulation_indices)
            warm_side_breathers = [idx for idx in breather_indices if idx < last_ins_idx]
            if warm_side_breathers:
                warnings.append(
                    "Breather membrane appears on the warm side of the insulation zone. "
                    "It should be cold-side / outboard."
                )

    # ── Cladding / external finish check ────────────────────────────────────
    if not any(l.role in _CLADDING_ROLES for l in layers):
        warnings.append("No cladding / external finish layer defined.")

    # ── Framing fraction check ───────────────────────────────────────────────
    for i, layer in enumerate(layers):
        if layer.role == "framing_zone" and layer.framing_fraction == 0.0:
            warnings.append(
                f"Layer {i + 1} '{layer.name}' has role 'framing_zone' but no framing fraction set. "
                "Add a framing fraction (e.g. 0.15 for 47mm studs at 600cc)."
            )

    # ── Cavity note ──────────────────────────────────────────────────────────
    has_cavity = any(l.role == "cavity" for l in layers)
    if has_cavity:
        warnings.append(
            "Ventilated cavity detected — thermal resistance excluded from calculation (conservative)."
        )

    # ── U-value calculation ──────────────────────────────────────────────────
    # Always attempt calculation from valid thermal layers, regardless of
    # validation errors, so the UI can show a live number while errors are shown.
    thermal_layers = [
        l for l in layers
        if l.include_in_u_value and l.thickness_mm > 0 and l.lambda_W_mK > 0
    ]

    u_value = 0.0
    r_total = 0.0
    layer_results: list[LayerResult] = []

    et = element_type if element_type in ("ExternalWall", "Floor", "Roof") else "ExternalWall"

    if thermal_layers:
        uv_layers = [
            UValueLayer(
                name=l.name,
                thickness_mm=l.thickness_mm,
                lambda_W_mK=(
                    l.infill_lambda_W_mK
                    if (l.infill_lambda_W_mK and l.role == "framing_zone")
                    else l.lambda_W_mK
                ),
                framing_fraction=l.framing_fraction,
                lambda_framing=l.lambda_framing,
            )
            for l in thermal_layers
        ]
        uv_result = calculate_u_value(et, uv_layers, target_u=1.0)
        u_value = uv_result.u_value
        r_total = uv_result.r_total
        layer_results = uv_result.layers

    # ── Target checks ────────────────────────────────────────────────────────
    target_results: list[TargetResult] = []
    if u_value > 0:
        for code, targets in _TARGETS.items():
            target_u = targets.get(et, 0.18)
            passes = u_value <= target_u
            target_results.append(TargetResult(
                code=code,
                element_type=et,
                target_u_value=target_u,
                passes=passes,
                headroom=round(target_u - u_value, 4),
                label=f"{code} profile target — preliminary check",
            ))

    # ── Total build-up thickness (all layers, not just thermal) ──────────────
    total_thickness_mm = round(sum(l.thickness_mm for l in layers), 1)

    # ── Assumptions ──────────────────────────────────────────────────────────
    assumptions: list[str] = [
        "Layer order is inside-to-outside.",
        f"Surface resistance profile: {et} (ISO 6946:2017 Table 1).",
        "Membranes excluded from thermal resistance.",
    ]
    if has_cavity:
        assumptions.append("Ventilated cavity excluded or handled conservatively (ISO 6946).")
    if any(l.framing_fraction > 0 for l in layers):
        assumptions.append(
            "Timber fraction applied to framing zones (parallel path method, ISO 6946 Annex E)."
        )
    assumptions.append("Preliminary check — for professional review only.")

    return ResolverResult(
        u_value=u_value,
        r_total=r_total,
        total_thickness_mm=total_thickness_mm,
        layers=layer_results,
        errors=errors,
        warnings=warnings,
        targets=target_results,
        assumptions=assumptions,
    )
