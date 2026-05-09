"""
Skill: Drawing Generator

Generates SVG drawings for a pod factory pack:
  - floor_plan_svg()      — top-down plan view with opening indicators
  - wall_elevation_svg()  — framing layout for one wall face
  - generate_drawings()   — convenience wrapper that returns all five drawings

Floor plan orientation
──────────────────────
  Long axis (length_m) runs horizontally (E–W in the drawing).
  Short axis (width_m) runs vertically.
  N wall at top, S wall at bottom — consistent with the element_decomposer
  convention where N/S are the long walls (span = length_m).

Wall elevation coordinate system
──────────────────────────────────
  x increases left → right along the wall span.
  y increases top → bottom (standard SVG).
  Sole plate at the bottom, top plate at the top.
  Stud positions are schematic when openings are present (exact positions
  come from the architect drawing; factory pack shows structural intent).

SVG drawing constants
──────────────────────
  SCALE  = 80 px / metre
  MARGIN = 80 px on all sides (dimension annotations + labels)
"""
import math
from app.skills.element_decomposer import DecomposedElement
from app.skills.sales_sheet_generator import sales_sheet_svg

# ── Constants ─────────────────────────────────────────────────────────────────
SCALE    = 80     # px per metre
MARGIN   = 80     # px around drawing for annotations
PLATE_H  = 0.045  # m — visual plate thickness (proportional, not actual)

# Technical-drawing colour palette
_BG         = "white"
_WALL_FILL  = "#F5F5F5"
_WALL_LINE  = "#333333"
_STUD       = "#8B6340"   # timber warm brown
_PLATE_FILL = "#7B5230"
_OPEN_FILL  = "#EBF5FB"
_OPEN_LINE  = "#1A73C8"
_LINTEL     = "#0D47A1"
_DIM        = "#888888"
_DIM_RED    = "#CC2200"   # manufacture-suite red dimension strings
_LABEL      = "#222222"
_FONT       = "Arial, Helvetica, sans-serif"

# Manufacture-plan sheet constants (px at SCALE=80)
_TITLE_H  = 85   # height of title block strip at bottom
_BORDER_I = 12   # inner margin from sheet edge to border line

# ── Central dimension style (manufacture plan) ────────────────────────────────
# Change these values to restyle ALL dimension annotations at once.
_DS_FONT   = 20    # dimension text font size (px) — readable at A3 on screen
_DS_ARROW  = 12    # arrowhead half-size (px)
_DS_LINE_W = 0.8   # dimension line stroke width (unchanged)
_DS_TICK   = 5     # extension line tick (px beyond dim line)
_DS_STEP   = 36    # px between stacked dimension levels (level 0 closest)


# ── SVG primitives ────────────────────────────────────────────────────────────

def _px(m: float) -> float:
    return m * SCALE


def _r(x, y, w, h, fill=_WALL_FILL, stroke=_WALL_LINE, sw=1.0) -> str:
    return (f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')


def _l(x1, y1, x2, y2, stroke=_WALL_LINE, sw=1.0, dash="") -> str:
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
            f'stroke="{stroke}" stroke-width="{sw}"{d}/>')


def _t(x, y, text, size=11, anchor="middle", fill=_LABEL,
       weight="normal", rotate=None) -> str:
    xf = f' transform="rotate({rotate[0]},{rotate[1]:.1f},{rotate[2]:.1f})"' if rotate else ""
    return (f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" '
            f'font-family="{_FONT}" font-size="{size}" fill="{fill}" '
            f'font-weight="{weight}"{xf}>{text}</text>')


def _arrow_h(x: float, y: float, dir: int) -> str:
    """Horizontal filled arrowhead. dir: +1 = right, -1 = left."""
    pts = (f"{x:.1f},{y:.1f} "
           f"{x - dir*7:.1f},{y - 3:.1f} "
           f"{x - dir*7:.1f},{y + 3:.1f}")
    return f'<polygon points="{pts}" fill="{_DIM}"/>'


def _arrow_v(x: float, y: float, dir: int) -> str:
    """Vertical filled arrowhead. dir: +1 = down, -1 = up."""
    pts = (f"{x:.1f},{y:.1f} "
           f"{x - 3:.1f},{y - dir*7:.1f} "
           f"{x + 3:.1f},{y - dir*7:.1f}")
    return f'<polygon points="{pts}" fill="{_DIM}"/>'


def _dim_h(x1: float, x2: float, y_edge: float, label: str, below: bool = True) -> str:
    """Horizontal dimension annotation."""
    offset = 28 if below else -28
    yd = y_edge + offset
    ye1 = y_edge + (4 if below else -4)
    ye2 = yd + (8 if below else -8)
    out = [_l(x1, ye1, x1, ye2, _DIM, 0.7),
           _l(x2, ye1, x2, ye2, _DIM, 0.7),
           _l(x1 + 5, yd, x2 - 5, yd, _DIM, 0.7),
           _arrow_h(x1, yd, -1),
           _arrow_h(x2, yd, +1)]
    ty = yd + (12 if below else -5)
    out.append(_t((x1 + x2) / 2, ty, label, 9, "middle", _DIM))
    return "".join(out)


def _dim_v(y1: float, y2: float, x_edge: float, label: str, left: bool = True) -> str:
    """Vertical dimension annotation."""
    offset = -28 if left else 28
    xd = x_edge + offset
    xe1 = x_edge + (-4 if left else 4)
    xe2 = xd + (-8 if left else 8)
    out = [_l(xe1, y1, xe2, y1, _DIM, 0.7),
           _l(xe1, y2, xe2, y2, _DIM, 0.7),
           _l(xd, y1 + 5, xd, y2 - 5, _DIM, 0.7),
           _arrow_v(xd, y1, -1),
           _arrow_v(xd, y2, +1)]
    mx = xd + (-12 if left else 12)
    my = (y1 + y2) / 2
    out.append(_t(mx, my, label, 9, "middle", _DIM, rotate=(-90, mx, my)))
    return "".join(out)


def _mm(m: float) -> str:
    """Format metres as mm integer string."""
    return str(round(m * 1000))


# ── Stud layout helpers ───────────────────────────────────────────────────────

def _schematic_x(wall_span_m: float, opening_widths: list[float]) -> list[float]:
    """
    Distribute openings evenly along a wall for schematic positioning.
    Returns x_start (in metres from left) for each opening.
    """
    n = len(opening_widths)
    if n == 0:
        return []
    section = wall_span_m / (n + 1)
    result = []
    for i, w in enumerate(opening_widths):
        center = (i + 1) * section
        x = max(0.0, min(center - w / 2.0, wall_span_m - w))
        result.append(round(x, 4))
    return result


def stud_positions(
    wall_span_m: float,
    spacing_mm: int,
    opening_xs: list[float],
    opening_ws: list[float],
) -> list[float]:
    """
    Calculate stud centre-line positions (metres from left edge).
    - Regular studs at spacing_mm intervals (start and end studs always present)
    - King studs added at each opening edge
    - Studs inside opening clear width removed
    """
    sp = spacing_mm / 1000.0
    n_full = int(wall_span_m / sp)
    regular = [round(i * sp, 6) for i in range(n_full + 1)]
    if abs(regular[-1] - wall_span_m) > 0.001:
        regular.append(wall_span_m)

    kings = []
    for xs, w in zip(opening_xs, opening_ws):
        kings += [xs, xs + w]

    all_x = sorted(set(round(x, 4) for x in regular + kings
                       if -0.001 <= x <= wall_span_m + 0.001))

    result = []
    for x in all_x:
        inside = any(xs < x < xs + w for xs, w in zip(opening_xs, opening_ws))
        if not inside:
            result.append(x)
    return result


# ── Drawing functions ─────────────────────────────────────────────────────────

def wall_elevation_svg(
    face: str,
    wall_span_m: float,
    wall_height_m: float,
    openings: list[dict],
    stud_spacing_mm: int = 600,
) -> str:
    """
    Generate a wall elevation SVG showing the framing layout.

    Parameters
    ----------
    face            Wall face label: "N", "S", "E", or "W"
    wall_span_m     Horizontal span of the wall in metres
    wall_height_m   Eaves height in metres
    openings        List of dicts: {type, width_m, height_m, sill_height_m}
    stud_spacing_mm Stud centre-to-centre spacing in mm
    """
    w = _px(wall_span_m)
    h = _px(wall_height_m)
    ph = _px(PLATE_H)

    svg_w = int(w + 2 * MARGIN)
    svg_h = int(h + 2 * MARGIN + 36)
    ox, oy = MARGIN, MARGIN
    y_floor = oy + h
    y_top   = oy

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {svg_w} {svg_h}">',
        _r(0, 0, svg_w, svg_h, _BG, "none"),
        _r(ox, oy, w, h, _WALL_FILL, _WALL_LINE, 1.5),
        # top plate
        _r(ox, y_top, w, ph, _PLATE_FILL, _WALL_LINE, 0.8),
        # sole plate
        _r(ox, y_floor - ph, w, ph, _PLATE_FILL, _WALL_LINE, 0.8),
    ]

    # Opening positions — use x_offset_m when given, otherwise schematic
    # NOTE: use ow_m (opening width metres) — never shadow the outer w (wall px)
    o_ws = [o["width_m"] for o in openings]
    schematic_xs = _schematic_x(wall_span_m, o_ws)
    o_xs = []
    o_offset_explicit = []   # track which openings have an explicit offset
    for o, sx in zip(openings, schematic_xs):
        xoff = o.get("x_offset_m")
        ow_m = o["width_m"]
        if xoff is not None:
            left = float(xoff)   # x_offset_m = left edge/tangent for all shapes
        else:
            left = sx
        left = max(0.0, min(left, wall_span_m - ow_m))
        o_xs.append(left)
        o_offset_explicit.append(xoff is not None)

    studs = stud_positions(wall_span_m, stud_spacing_mm, o_xs, o_ws)

    # Studs (centre lines between plates)
    sy1 = y_top + ph
    sy2 = y_floor - ph
    for sx in studs:
        parts.append(_l(ox + _px(sx), sy1, ox + _px(sx), sy2, _STUD, 1.5))

    # Openings
    for o, o_x, was_explicit in zip(openings, o_xs, o_offset_explicit):
        shape = o.get("shape", "rectangular")
        sill = _px(o.get("sill_height_m", 0.0))

        if shape == "circular":
            r_m = o["width_m"] / 2.0
            r_px = _px(r_m)
            cx_px = ox + _px(o_x + r_m)        # centre x (o_x is left tangent)
            cy_px = y_floor - sill - r_px        # sill = bottom tangent; centre is r above
            parts.append(
                f'<circle cx="{cx_px:.1f}" cy="{cy_px:.1f}" r="{r_px:.1f}" '
                f'fill="{_OPEN_FILL}" stroke="{_OPEN_LINE}" stroke-width="1.5"/>'
            )
            tag = f"Ø{_mm(o['width_m'])}"
            parts.append(_t(cx_px, cy_px + 4, tag, 8, "middle", _OPEN_LINE))
            if o.get("sill_height_m", 0) > 0.001:
                bottom_y = y_floor - sill
                parts.append(_dim_v(bottom_y, y_floor, cx_px - r_px,
                                    f"{_mm(o['sill_height_m'])}↑", left=False))
        else:
            ow = _px(o["width_m"])
            oh = _px(o["height_m"])
            rx = ox + _px(o_x)
            ry = y_floor - sill - oh
            parts += [
                _r(rx, ry, ow, oh, _OPEN_FILL, _OPEN_LINE, 1.5),
                _l(rx, ry, rx + ow, ry, _LINTEL, 2.5),
            ]
            tag = f"{o['type'][0].upper()}  {_mm(o['width_m'])}×{_mm(o['height_m'])}"
            parts.append(_t(rx + ow / 2, ry + oh / 2 + 4, tag, 8, "middle", _OPEN_LINE))
            if o.get("sill_height_m", 0) > 0.001:
                parts.append(_dim_v(y_floor - sill, y_floor, rx,
                                    f"{_mm(o['sill_height_m'])}↑", left=False))
            # Offset-from-left dimension — shown whenever offset > 0
            if o_x > 0.001:
                parts.append(_dim_h(ox, rx, y_floor,
                                    f"{_mm(o_x)}", below=True))

    # Dimension annotations
    parts.append(_dim_h(ox, ox + w, y_floor, f"{_mm(wall_span_m)} mm", below=True))
    parts.append(_dim_v(oy, y_floor, ox, f"{_mm(wall_height_m)} mm", left=True))
    if len(studs) >= 2:
        dx1, dx2 = studs[0], studs[1]
        if dx2 > dx1:
            parts.append(_dim_h(ox + _px(dx1), ox + _px(dx2), oy,
                                f"@{stud_spacing_mm}", below=False))

    # Title
    parts.append(_t(svg_w / 2, svg_h - 12,
                    f"Wall {face}  —  {wall_span_m:.1f}m × {wall_height_m:.1f}m  "
                    f"studs @ {stud_spacing_mm}mm c/c",
                    11, "middle", _LABEL, "bold"))
    parts.append("</svg>")
    return "\n".join(parts)


def floor_plan_svg(
    width_m: float,
    length_m: float,
    openings: list[dict],
    wall_thick_m: float = 0.30,
    pod_name: str = "",
    roof_openings: list[dict] | None = None,
    wall_u_value: float | None = None,
    floor_u_value: float | None = None,
    roof_u_value: float | None = None,
) -> str:
    """
    Generate a floor plan SVG (top-down view).

    Convention: long axis (length_m) drawn horizontally.
    N wall at top, S wall at bottom, W at left, E at right.

    Parameters
    ----------
    width_m       Pod short dimension (N–S span)
    length_m      Pod long dimension (E–W span)
    openings      List of dicts: {wall, type, width_m, height_m, sill_height_m, x_offset_m}
    wall_thick_m  Actual wall build-up thickness in metres
    pod_name      Pod/project name shown centred in room
    roof_openings List of {selected, width_mm, height_mm, x_offset_mm, y_offset_mm}
    *_u_value     Optional U-values for annotation panel
    """
    ew  = _px(length_m)
    ns  = _px(width_m)
    WT  = _px(wall_thick_m)   # true wall thickness in px

    # Extra space on right for U-value panel if we have values
    uval_panel_w = 130 if (wall_u_value or floor_u_value or roof_u_value) else 0
    svg_w = int(ew + 2 * MARGIN + uval_panel_w)
    svg_h = int(ns + 2 * MARGIN + 50)
    ox, oy = MARGIN, MARGIN

    # Interior rectangle
    ix, iy = ox + WT, oy + WT
    iw, ih = ew - 2 * WT, ns - 2 * WT
    cx, cy = ox + ew / 2, oy + ns / 2   # plan centre

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {svg_w} {svg_h}">',
        _r(0, 0, svg_w, svg_h, _BG, "none"),
        # Outer wall solid fill
        _r(ox, oy, ew, ns, _WALL_FILL, _WALL_LINE, 2.0),
        # Interior void
        _r(ix, iy, iw, ih, "white", _WALL_LINE, 0.8),
    ]

    # ── Compass (top-right corner) ─────────────────────────────────────────────
    ncx, ncy = ox + ew + 24, oy + 18
    parts += [
        _l(ncx, ncy + 14, ncx, ncy - 14, "#333", 1.5),
        _l(ncx, ncy - 14, ncx - 4, ncy - 5, "#333", 1.5),
        _l(ncx, ncy - 14, ncx + 4, ncy - 5, "#333", 1.5),
        _t(ncx, ncy - 18, "N", 10, "middle", "#333", "bold"),
    ]

    # ── Opening counters ────────────────────────────────────────────────────────
    by_wall: dict[str, list[dict]] = {"N": [], "S": [], "E": [], "W": []}
    for o in openings:
        wall = o.get("wall", "")
        if wall in by_wall:
            by_wall[wall].append(o)

    door_n = window_n = french_n = 0

    def _opening_label(o_type):
        nonlocal door_n, window_n, french_n
        if o_type == "door":
            door_n += 1; return f"D{door_n}", "Door"
        if o_type == "french_door":
            french_n += 1; return f"FD{french_n}", "French Door"
        window_n += 1; return f"W{window_n}", "Window"

    def _plan_pos_m(span_m, items):
        schematic = _schematic_x(span_m, [o["width_m"] for o in items])
        result = []
        for o, sx in zip(items, schematic):
            xoff = o.get("x_offset_m")
            result.append(float(xoff) if xoff is not None else sx)
        return result

    # Track used offset dim y-levels to avoid overlap
    ns_dim_below_y: dict[str, float] = {}   # face → next available y
    ew_dim_right_x: dict[str, float] = {}

    def _dim_h_at(x1, x2, y_base, label, below, level=0):
        """Offset dim with stacking levels to avoid overlap."""
        off = 22 + level * 18
        yd  = y_base + (off if below else -off)
        ye  = y_base + (3  if below else -3)
        out = [_l(x1, ye, x1, yd, _DIM, 0.6),
               _l(x2, ye, x2, yd, _DIM, 0.6),
               _l(x1+4, yd, x2-4, yd, _DIM, 0.7),
               _arrow_h(x1, yd, -1), _arrow_h(x2, yd, +1)]
        ty = yd + (10 if below else -3)
        out.append(_t((x1+x2)/2, ty, label, 8, "middle", _DIM))
        return "".join(out)

    def _dim_v_at(y1, y2, x_base, label, left, level=0):
        off = 22 + level * 18
        xd  = x_base + (-off if left else off)
        xe  = x_base + (-3  if left else 3)
        out = [_l(xe, y1, xd, y1, _DIM, 0.6),
               _l(xe, y2, xd, y2, _DIM, 0.6),
               _l(xd, y1+4, xd, y2-4, _DIM, 0.7),
               _arrow_v(xd, y1, -1), _arrow_v(xd, y2, +1)]
        mx, my = xd + (-10 if left else 10), (y1+y2)/2
        out.append(_t(mx, my, label, 8, "middle", _DIM, rotate=(-90, mx, my)))
        return "".join(out)

    # ── N/S wall openings (along E-W axis) ────────────────────────────────────
    for face, wall_y, is_n in (("N", oy, True), ("S", oy + ns - WT, False)):
        wo_list = by_wall[face]
        xs_m = _plan_pos_m(length_m, wo_list)
        dim_level = 0
        for o, x_m in zip(wo_list, xs_m):
            label, _ = _opening_label(o["type"])
            ow_px = _px(o["width_m"])
            rx = ox + _px(x_m)
            # Opening gap (white over wall)
            parts.append(_r(rx, wall_y, ow_px, WT, "white", "none"))
            # Opening line
            mid_y = wall_y + WT / 2
            parts.append(_l(rx, mid_y, rx + ow_px, mid_y, _OPEN_LINE, 2.0))
            # Door swing
            if o["type"] in ("door", "french_door"):
                swing_r = ow_px
                interior_y = iy if is_n else iy + ih
                swing_dir = 1 if is_n else -1
                parts.append(
                    f'<path d="M {rx:.1f} {interior_y:.1f} '
                    f'L {rx:.1f} {interior_y + swing_dir*swing_r:.1f}" '
                    f'stroke="{_DIM}" stroke-width="0.8" stroke-dasharray="4,3" fill="none"/>'
                )
                parts.append(
                    f'<path d="M {rx:.1f} {interior_y + swing_dir*swing_r:.1f} '
                    f'A {swing_r:.1f} {swing_r:.1f} 0 0 {"1" if is_n else "0"} '
                    f'{rx + ow_px:.1f} {interior_y:.1f}" '
                    f'stroke="{_DIM}" stroke-width="0.8" stroke-dasharray="4,3" fill="none"/>'
                )
            # Label
            ref_y = wall_y if is_n else wall_y + WT
            label_y = ref_y + (-5 if is_n else 12)
            w_mm = int(o["width_m"] * 1000)
            h_mm = int(o["height_m"] * 1000)
            parts.append(_t(rx + ow_px/2, label_y, label, 8, "middle", _OPEN_LINE, "bold"))
            parts.append(_t(rx + ow_px/2, label_y + (11 if not is_n else -11),
                           f"{w_mm}×{h_mm}", 7, "middle", _DIM))
            # Offset dimension from corner
            if x_m > 0.001:
                ref_dim_y = oy if is_n else oy + ns
                below = not is_n
                parts.append(_dim_h_at(ox, rx, ref_dim_y, f"{_mm(x_m)}", below, dim_level))
                dim_level += 1
            # Width dimension
            parts.append(_dim_h_at(rx, rx + ow_px, ref_y,
                                   f"{int(o['width_m']*1000)}", not is_n, dim_level))

    # ── E/W wall openings (along N-S axis) ─────────────────────────────────────
    for face, wall_x, is_w in (("W", ox, True), ("E", ox + ew - WT, False)):
        wo_list = by_wall[face]
        ys_m = _plan_pos_m(width_m, wo_list)
        dim_level = 0
        for o, y_m in zip(wo_list, ys_m):
            label, _ = _opening_label(o["type"])
            ow_px = _px(o["width_m"])
            ry = oy + _px(y_m)
            # Opening gap
            parts.append(_r(wall_x, ry, WT, ow_px, "white", "none"))
            mid_x = wall_x + WT / 2
            parts.append(_l(mid_x, ry, mid_x, ry + ow_px, _OPEN_LINE, 2.0))
            # Door swing
            if o["type"] in ("door", "french_door"):
                swing_r = ow_px
                interior_x = ix + iw if is_w else ix
                swing_dir = 1 if is_w else -1
                parts.append(
                    f'<path d="M {interior_x:.1f} {ry:.1f} '
                    f'L {interior_x + swing_dir*swing_r:.1f} {ry:.1f}" '
                    f'stroke="{_DIM}" stroke-width="0.8" stroke-dasharray="4,3" fill="none"/>'
                )
                parts.append(
                    f'<path d="M {interior_x + swing_dir*swing_r:.1f} {ry:.1f} '
                    f'A {swing_r:.1f} {swing_r:.1f} 0 0 {"0" if is_w else "1"} '
                    f'{interior_x:.1f} {ry + ow_px:.1f}" '
                    f'stroke="{_DIM}" stroke-width="0.8" stroke-dasharray="4,3" fill="none"/>'
                )
            # Label
            ref_x = wall_x if is_w else wall_x + WT
            label_x = ref_x + (-8 if is_w else 8)
            w_mm = int(o["width_m"] * 1000)
            h_mm = int(o["height_m"] * 1000)
            parts.append(_t(label_x, ry + ow_px/2, label, 8, "middle" if not is_w else "end", _OPEN_LINE, "bold"))
            parts.append(_t(label_x, ry + ow_px/2 + 12,
                           f"{w_mm}×{h_mm}", 7, "middle" if not is_w else "end", _DIM))
            # Offset dim
            if y_m > 0.001:
                ref_dim_x = ox if is_w else ox + ew
                left = is_w
                parts.append(_dim_v_at(oy, ry, ref_dim_x, f"{_mm(y_m)}", left, dim_level))
                dim_level += 1
            # Height dimension
            parts.append(_dim_v_at(ry, ry + ow_px, ref_x,
                                   f"{int(o['width_m']*1000)}", is_w, dim_level))

    # ── Roof openings (skylights) ──────────────────────────────────────────────
    rl_n = 0
    for ro in (roof_openings or []):
        if not ro.get("selected", False):
            continue
        rl_n += 1
        rw_m = float(ro.get("width_mm", 600)) / 1000
        rh_m = float(ro.get("height_mm", 900)) / 1000
        rx_off = ro.get("x_offset_mm")
        ry_off = ro.get("y_offset_mm")
        # Position in plan (interior coordinates)
        ri_w = length_m - 2 * wall_thick_m
        ri_h = width_m - 2 * wall_thick_m
        rx_m = float(rx_off)/1000 if rx_off not in (None,"") else (ri_w - rw_m) / 2
        ry_m = float(ry_off)/1000 if ry_off not in (None,"") else (ri_h - rh_m) / 2
        # px position from outer corner
        rpx = ix + _px(rx_m)
        rpy = iy + _px(ry_m)
        rw_px = _px(rw_m)
        rh_px = _px(rh_m)
        parts.append(_r(rpx, rpy, rw_px, rh_px, "#DBEAFE", "#2563EB", 1.2))
        # dashes overlay
        parts.append(
            f'<rect x="{rpx:.1f}" y="{rpy:.1f}" width="{rw_px:.1f}" height="{rh_px:.1f}" '
            f'fill="none" stroke="#2563EB" stroke-width="0.8" stroke-dasharray="5,3"/>'
        )
        rl_label = f"RL{rl_n}"
        parts.append(_t(rpx + rw_px/2, rpy + rh_px/2 + 4, rl_label, 9, "middle", "#1d4ed8", "bold"))
        w_mm_str = int(rw_m * 1000)
        h_mm_str = int(rh_m * 1000)
        parts.append(_t(rpx + rw_px/2, rpy - 5, f"{w_mm_str}×{h_mm_str}", 7, "middle", "#2563EB"))
        # x-offset dim: horizontal line below the rooflight, from interior W wall to RL left edge
        xdoff = 12
        yd_x  = rpy + rh_px + xdoff
        if rpx - ix > 4:
            parts += [
                _l(ix,  rpy + rh_px * 0.5, ix,  yd_x + 4, _DIM, 0.5),
                _l(rpx, rpy + rh_px,        rpx, yd_x + 4, _DIM, 0.5),
                _l(ix + 4, yd_x, rpx - 4, yd_x, _DIM, 0.8),
                _arrow_h(ix,  yd_x, +1), _arrow_h(rpx, yd_x, -1),
                _t((ix + rpx) / 2, yd_x + 10, f"{int(rx_m*1000)}", 7, "middle", _DIM),
            ]
        # y-offset dim: vertical line left of the rooflight, from interior N wall to RL top edge
        ydoff = 12
        xd_y  = rpx - ydoff
        if rpy - iy > 4:
            parts += [
                _l(rpx - rw_px * 0.5, iy,  xd_y - 4, iy,  _DIM, 0.5),
                _l(rpx,               rpy, xd_y - 4, rpy, _DIM, 0.5),
                _l(xd_y, iy + 4, xd_y, rpy - 4, _DIM, 0.8),
                _arrow_v(xd_y, iy,  +1), _arrow_v(xd_y, rpy, -1),
            ]
            mx, my = xd_y - 10, (iy + rpy) / 2
            parts.append(_t(mx, my, f"{int(ry_m*1000)}", 7, "middle", _DIM,
                            rotate=(-90, mx, my)))

    # ── Wall thickness annotation ──────────────────────────────────────────────
    # Small double-headed arrow showing WT on the south wall
    twx1, twx2 = ox + ew * 0.72, ox + ew * 0.72
    twy1, twy2 = oy + ns - WT, oy + ns
    parts += [
        _l(twx1 - 8, twy1, twx2 + 8, twy1, _DIM, 0.5),
        _l(twx1 - 8, twy2, twx2 + 8, twy2, _DIM, 0.5),
        _l(twx1, twy1, twx1, twy2, _DIM, 0.8),
        _arrow_v(twx1, twy1, -1), _arrow_v(twx1, twy2, +1),
        _t(twx1 + 14, (twy1 + twy2) / 2 + 3, f"Wall {int(wall_thick_m*1000)}mm", 7, "start", _DIM),
    ]

    # ── Room annotation (pod name + floor area) ────────────────────────────────
    floor_area = (length_m - 2*wall_thick_m) * (width_m - 2*wall_thick_m)
    if pod_name:
        parts.append(_t(cx, cy - 8, pod_name, 10, "middle", "#666", "bold"))
    parts.append(_t(cx, cy + (8 if pod_name else 4),
                    f"{floor_area:.1f} m²", 10, "middle", "#999"))

    # ── Outer dimension annotations ────────────────────────────────────────────
    parts.append(_dim_h(ox, ox + ew, oy, f"{int(length_m*1000)} mm", below=False))
    parts.append(_dim_v(oy, oy + ns, ox + ew + (uval_panel_w or 0), f"{int(width_m*1000)} mm", left=False))

    # ── U-value panel (right of plan) ──────────────────────────────────────────
    if uval_panel_w:
        px0 = ox + ew + 18
        py0 = oy + 4
        row_h = 22
        label_col = [
            ("Wall U-value",  f"{wall_u_value:.3f} W/m²K"  if wall_u_value  else "—"),
            ("Floor U-value", f"{floor_u_value:.3f} W/m²K" if floor_u_value else "—"),
            ("Roof U-value",  f"{roof_u_value:.3f} W/m²K"  if roof_u_value  else "—"),
            ("Wall thick.",   f"{int(wall_thick_m*1000)} mm"),
            ("Floor area",    f"{floor_area:.1f} m²"),
        ]
        parts.append(_r(px0 - 4, py0 - 2, uval_panel_w - 14, row_h * len(label_col) + 12, "#F9F9F9", "#CCCCCC", 0.6))
        parts.append(_t(px0 + (uval_panel_w-14)//2, py0 + 8, "Target U-values", 8, "middle", _LABEL, "bold"))
        for i, (lbl, val) in enumerate(label_col):
            yrow = py0 + 18 + i * row_h
            parts.append(_t(px0, yrow, lbl, 7.5, "start", _DIM))
            parts.append(_t(px0 + uval_panel_w - 18, yrow, val, 8, "end", _LABEL, "bold"))
            parts.append(_l(px0 - 4, yrow + 6, px0 + uval_panel_w - 18, yrow + 6, "#EEEEEE", 0.5))

    # ── Title block ────────────────────────────────────────────────────────────
    title = f"Floor Plan  —  {length_m:.2f}m × {width_m:.2f}m   Wall {int(wall_thick_m*1000)}mm"
    if pod_name:
        title = f"{pod_name}  ·  " + title
    parts.append(_t(svg_w / 2, svg_h - 10,
                    title, 11, "middle", _LABEL, "bold"))
    parts.append("</svg>")
    return "\n".join(parts)


def _mfr_arrow_h(x: float, y: float, dir: int, color: str = _DIM_RED) -> str:
    """Horizontal arrowhead using central dim style."""
    a, h = _DS_ARROW, _DS_ARROW // 2
    pts = (f"{x:.1f},{y:.1f} "
           f"{x - dir*a:.1f},{y - h:.1f} "
           f"{x - dir*a:.1f},{y + h:.1f}")
    return f'<polygon points="{pts}" fill="{color}"/>'


def _mfr_arrow_v(x: float, y: float, dir: int, color: str = _DIM_RED) -> str:
    """Vertical arrowhead using central dim style."""
    a, h = _DS_ARROW, _DS_ARROW // 2
    pts = (f"{x:.1f},{y:.1f} "
           f"{x - h:.1f},{y - dir*a:.1f} "
           f"{x + h:.1f},{y - dir*a:.1f}")
    return f'<polygon points="{pts}" fill="{color}"/>'


def _mfr_dim_h(x1: float, x2: float, y_edge: float, label: str,
               below: bool = True, color: str = _DIM_RED) -> str:
    """Horizontal chain dimension string in manufacture red."""
    offset = 26 if below else -26
    yd  = y_edge + offset
    ye1 = y_edge + (3 if below else -3)
    ye2 = yd + (7 if below else -7)
    out = [_l(x1, ye1, x1, ye2, color, 0.7),
           _l(x2, ye1, x2, ye2, color, 0.7),
           _l(x1 + 5, yd, x2 - 5, yd, color, 0.8),
           _mfr_arrow_h(x1, yd, -1, color),
           _mfr_arrow_h(x2, yd, +1, color)]
    ty = yd + (11 if below else -4)
    out.append(_t((x1 + x2) / 2, ty, label, 8, "middle", color, "bold"))
    return "".join(out)


def _mfr_dim_v(y1: float, y2: float, x_edge: float, label: str,
               left: bool = True, color: str = _DIM_RED) -> str:
    """Vertical chain dimension string in manufacture red."""
    offset = -26 if left else 26
    xd  = x_edge + offset
    xe1 = x_edge + (-3 if left else 3)
    xe2 = xd + (-7 if left else 7)
    out = [_l(xe1, y1, xe2, y1, color, 0.7),
           _l(xe1, y2, xe2, y2, color, 0.7),
           _l(xd, y1 + 5, xd, y2 - 5, color, 0.8),
           _mfr_arrow_v(xd, y1, -1, color),
           _mfr_arrow_v(xd, y2, +1, color)]
    mx = xd + (-11 if left else 11)
    my = (y1 + y2) / 2
    out.append(_t(mx, my, label, 8, "middle", color, "bold", rotate=(-90, mx, my)))
    return "".join(out)


def _mfr_tag(cx: float, cy: float, tag: str, size: int = 13) -> str:
    """Opening tag badge — white box with blue border and bold label."""
    tw = max(32, len(tag) * (size - 2) + 10)
    th = size + 8
    tx = cx - tw / 2
    ty = cy - th / 2
    out = [f'<rect x="{tx:.1f}" y="{ty:.1f}" width="{tw:.1f}" height="{th:.1f}" '
           f'fill="white" stroke="{_OPEN_LINE}" stroke-width="1.4" rx="2"/>',
           _t(cx, cy + size * 0.35, tag, size, "middle", _OPEN_LINE, "bold")]
    return "".join(out)


def manufacture_plan_svg(
    width_m: float,
    length_m: float,
    openings: list[dict],
    wall_thick_m: float = 0.25,
    pod_name: str = "",
    project_name: str = "",
    client_project_id: str = "",
    drawn_by: str = "",
    checked_by: str = "",
    revision: str = "P1",
    drawing_number: str = "",
    status: str = "Preliminary",
    issue_date: str = "",
    scale_str: str = "1:50",
    disclaimer: str = "This drawing is indicative only. All dimensions to be verified on site.",
    roof_openings: list[dict] | None = None,
) -> str:
    """
    Manufacture-suite floor plan SVG using a fixed-sheet coordinate system.

    Sheet (1200×850) has three protected zones:
      - Sheet border (20px inset line)
      - Drawing viewport (inside border, above title block)
      - Title block (150px band at bottom, inside border)

    The floor plan and ALL dimensions are scaled to fit within the
    drawing viewport.  Nothing touches the title block or sheet border.
    """
    # ── Fixed sheet dimensions ─────────────────────────────────────────────────
    SW, SH  = 1200, 850          # sheet
    BORD    = 20                 # sheet border line inset from edge
    TB_H    = 150                # title block height (bottom band)
    # Dim zone: 3 levels × _DS_STEP + text height + small margin
    DZ      = _DS_STEP * 3 + _DS_FONT + 10   # ≈ 138 px

    # ── Protected zones ────────────────────────────────────────────────────────
    # Drawing viewport (where everything except title block lives)
    vp_x = BORD + 4
    vp_y = BORD + 4
    vp_w = SW - 2 * (BORD + 4)
    vp_h = SH - TB_H - BORD - 4

    # Title block top edge
    tb_y = SH - TB_H - BORD

    # Plan zone (inside dim budget) — plan geometry is drawn here
    pz_x = vp_x + DZ
    pz_y = vp_y + DZ
    pz_w = vp_w - 2 * DZ
    pz_h = vp_h - 2 * DZ

    # ── Scale: fit plan inside plan zone ──────────────────────────────────────
    S = min(pz_w / length_m, pz_h / width_m)

    pw = length_m * S    # plan width in px
    ph = width_m  * S    # plan height in px
    # Centre plan within the plan zone
    ox = pz_x + (pz_w - pw) / 2
    oy = pz_y + (pz_h - ph) / 2

    WT = wall_thick_m * S
    ix, iy = ox + WT, oy + WT
    iw, ih = pw - 2 * WT, ph - 2 * WT
    cx, cy = ox + pw / 2, oy + ph / 2

    # ── Local dimension helpers — use central _DS_* style constants ───────────
    # Level 0 = opening widths (closest to wall)
    # Level 1 = chain/set-out dims
    # Level 2 = overall dim (furthest)

    def _hdim(x1, x2, y_ref, label, above=True, level=0):
        """Horizontal dim string.  above=True → dims go upward from y_ref."""
        sign = -1 if above else +1
        yd = y_ref + sign * (_DS_STEP * (level + 1))
        yt = y_ref + sign * _DS_TICK
        out = [_l(x1, yt, x1, yd, _DIM_RED, _DS_LINE_W),
               _l(x2, yt, x2, yd, _DIM_RED, _DS_LINE_W),
               _l(x1 + _DS_ARROW, yd, x2 - _DS_ARROW, yd, _DIM_RED, _DS_LINE_W),
               _mfr_arrow_h(x1, yd, -1),
               _mfr_arrow_h(x2, yd, +1)]
        ty = yd - 6 if above else yd + _DS_FONT + 4
        out.append(_t((x1 + x2) / 2, ty, label, _DS_FONT, "middle", _DIM_RED, "bold"))
        return "".join(out)

    def _vdim(y1, y2, x_ref, label, left=True, level=0):
        """Vertical dim string.  left=True → dims go leftward from x_ref."""
        sign = -1 if left else +1
        xd = x_ref + sign * (_DS_STEP * (level + 1))
        xt = x_ref + sign * _DS_TICK
        out = [_l(xt, y1, xd, y1, _DIM_RED, _DS_LINE_W),
               _l(xt, y2, xd, y2, _DIM_RED, _DS_LINE_W),
               _l(xd, y1 + _DS_ARROW, xd, y2 - _DS_ARROW, _DIM_RED, _DS_LINE_W),
               _mfr_arrow_v(xd, y1, -1),
               _mfr_arrow_v(xd, y2, +1)]
        mx = xd + (-(  _DS_FONT + 4) if left else (_DS_FONT + 4))
        my = (y1 + y2) / 2
        out.append(_t(mx, my, label, _DS_FONT, "middle", _DIM_RED, "bold", rotate=(-90, mx, my)))
        return "".join(out)

    # ── Part list ──────────────────────────────────────────────────────────────
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {SW} {SH}">',
        # Sheet background
        _r(0, 0, SW, SH, "#FFFFFF", "none"),
        # Sheet border line
        f'<rect x="{BORD}" y="{BORD}" width="{SW-2*BORD}" height="{SH-2*BORD}" '
        f'fill="none" stroke="#333333" stroke-width="1.5"/>',
        # Title block top divider
        _l(BORD, tb_y, SW - BORD, tb_y, "#333333", 1.2),
        # Plan geometry
        _r(ox, oy, pw, ph, _WALL_FILL, _WALL_LINE, 2.0),
        _r(ix, iy, iw, ih, "white", _WALL_LINE, 0.8),
    ]

    # ── North arrow — safe-zone placement ────────────────────────────────────
    # Plan + full dim zone bounding box (protected area)
    _N_R  = 22    # arrow circle radius
    _N_CL = 30    # minimum clearance from protected zones
    plan_left  = ox - DZ
    plan_right = ox + pw + DZ
    plan_top   = oy - DZ
    plan_bot   = oy + ph + DZ

    def _north_ok(cx, cy):
        r = _N_R + _N_CL
        if cx - r < vp_x or cx + r > vp_x + vp_w: return False
        if cy - r < vp_y or cy + r > tb_y - 10:   return False
        # clashes with plan+dim zone?
        if (cx + _N_R > plan_left and cx - _N_R < plan_right and
                cy + _N_R > plan_top  and cy - _N_R < plan_bot):
            return False
        return True

    _nm = _N_R + _N_CL + 8
    _candidates = [
        (vp_x + vp_w - _nm, vp_y + _nm),       # TR viewport
        (vp_x + _nm,        vp_y + _nm),        # TL viewport
        (vp_x + vp_w - _nm, tb_y - _nm),        # BR viewport (above TB)
        (vp_x + _nm,        tb_y - _nm),        # BL viewport (above TB)
    ]
    ncx, ncy = next(((cx, cy) for cx, cy in _candidates if _north_ok(cx, cy)),
                    _candidates[0])
    parts += [
        f'<circle cx="{ncx:.1f}" cy="{ncy:.1f}" r="{_N_R:.0f}" '
        f'fill="none" stroke="#444444" stroke-width="1.2"/>',
        _l(ncx, ncy + _N_R - 5, ncx, ncy - _N_R + 5, "#444", 1.5),
        _l(ncx, ncy - _N_R + 5, ncx - 5, ncy - _N_R + 14, "#444", 1.5),
        _l(ncx, ncy - _N_R + 5, ncx + 5, ncy - _N_R + 14, "#444", 1.5),
        _t(ncx, ncy + _N_R - 7, "N", 11, "middle", "#333", "bold"),
    ]

    # ── Opening schedule state ─────────────────────────────────────────────────
    by_wall: dict[str, list[dict]] = {"N": [], "S": [], "E": [], "W": []}
    for o in openings:
        w = o.get("wall", "")
        if w in by_wall:
            by_wall[w].append(o)

    # (tag, type_str, width_mm, height_mm, location)
    schedule: list[tuple[str, str, int, int, str]] = []
    door_n = window_n = french_n = 0

    def _make_tag(o_type: str) -> str:
        nonlocal door_n, window_n, french_n
        if o_type == "door":
            door_n += 1; return f"D{door_n}"
        if o_type == "french_door":
            french_n += 1; return f"FD{french_n}"
        window_n += 1; return f"W{window_n}"

    def _pos_m(span_m, items):
        sch = _schematic_x(span_m, [o["width_m"] for o in items])
        return [float(o.get("x_offset_m", sx)) if o.get("x_offset_m") is not None else sx
                for o, sx in zip(items, sch)]

    # ── N/S wall openings ──────────────────────────────────────────────────────
    for face, wall_y, above_plan in (("N", oy, True), ("S", oy + ph - WT, False)):
        wo = by_wall[face]
        xs_m = _pos_m(length_m, wo)
        prev_px = ox

        for i, (o, x_m) in enumerate(zip(wo, xs_m)):
            tag   = _make_tag(o["type"])
            ow_px = o["width_m"] * S
            rx    = ox + x_m * S
            schedule.append((tag, o["type"], int(o["width_m"]*1000),
                             int(o["height_m"]*1000), f"Wall {face}"))

            # Opening gap + centre line
            parts.append(_r(rx, wall_y, ow_px, WT, "white", "none"))
            parts.append(_l(rx, wall_y + WT/2, rx + ow_px, wall_y + WT/2, _OPEN_LINE, 2.0))

            # Door swing
            if o["type"] in ("door", "french_door"):
                int_y  = iy if above_plan else iy + ih
                sdir   = 1 if above_plan else -1
                parts.append(
                    f'<path d="M {rx:.1f} {int_y:.1f} '
                    f'L {rx:.1f} {int_y+sdir*ow_px:.1f}" '
                    f'stroke="{_DIM}" stroke-width="0.7" stroke-dasharray="4,3" fill="none"/>'
                )
                parts.append(
                    f'<path d="M {rx:.1f} {int_y+sdir*ow_px:.1f} '
                    f'A {ow_px:.1f} {ow_px:.1f} 0 0 {"1" if above_plan else "0"} '
                    f'{rx+ow_px:.1f} {int_y:.1f}" '
                    f'stroke="{_DIM}" stroke-width="0.7" stroke-dasharray="4,3" fill="none"/>'
                )

            # Tag badge + size label — placed INSIDE the pod footprint
            # N wall (above_plan=True): interior is below → offset inward from wall bottom face
            # S wall (above_plan=False): interior is above → offset inward from wall top face
            # tag_ofs = 46px keeps labels clear of red dimension chains on the exterior
            tag_ofs = 46
            if above_plan:
                ty = wall_y + WT + tag_ofs
                lbl_y = ty + 18
            else:
                ty = wall_y - tag_ofs
                lbl_y = ty - 18
            parts.append(_mfr_tag(rx + ow_px/2, ty, tag))
            size_lbl = f"{int(o['width_m']*1000)} × {int(o['height_m']*1000)}"
            parts.append(_t(rx + ow_px/2, lbl_y, size_lbl, _DS_FONT - 4, "middle", _OPEN_LINE))

            # Opening width dim (level 0, closest to wall)
            parts.append(_hdim(rx, rx + ow_px, wall_y if above_plan else wall_y + WT,
                               f"{int(o['width_m']*1000)}", above_plan, level=0))

            # Chain dim: from previous reference to this opening's left edge (level 1)
            gap_mm = int(x_m*1000) if i == 0 else int((x_m - xs_m[i-1] - wo[i-1]["width_m"])*1000)
            if rx - prev_px > 3:
                parts.append(_hdim(prev_px, rx,
                                   wall_y if above_plan else wall_y + WT,
                                   str(gap_mm), above_plan, level=1))
            prev_px = rx + ow_px

        # Tail chain dim: last opening right edge → E corner
        if wo:
            tail_mm = int((length_m - xs_m[-1] - wo[-1]["width_m"])*1000)
            tail_px = ox + pw - (ox + xs_m[-1]*S + wo[-1]["width_m"]*S)
            if tail_px > 3 and tail_mm > 0:
                parts.append(_hdim(
                    ox + xs_m[-1]*S + wo[-1]["width_m"]*S, ox + pw,
                    wall_y if above_plan else wall_y + WT,
                    str(tail_mm), above_plan, level=1
                ))

        # Overall E-W dim (level 2 — outermost)
        parts.append(_hdim(ox, ox + pw,
                           wall_y if above_plan else wall_y + WT,
                           f"{int(length_m*1000)}", above_plan, level=2))

    # ── E/W wall openings ──────────────────────────────────────────────────────
    for face, wall_x, left_of_plan in (("W", ox, True), ("E", ox + pw - WT, False)):
        wo   = by_wall[face]
        ys_m = _pos_m(width_m, wo)
        prev_py = oy

        for i, (o, y_m) in enumerate(zip(wo, ys_m)):
            tag   = _make_tag(o["type"])
            ow_px = o["width_m"] * S
            ry    = oy + y_m * S
            schedule.append((tag, o["type"], int(o["width_m"]*1000),
                             int(o["height_m"]*1000), f"Wall {face}"))

            parts.append(_r(wall_x, ry, WT, ow_px, "white", "none"))
            parts.append(_l(wall_x + WT/2, ry, wall_x + WT/2, ry + ow_px, _OPEN_LINE, 2.0))

            if o["type"] in ("door", "french_door"):
                int_x = ix + iw if left_of_plan else ix
                sdir  = 1 if left_of_plan else -1
                parts.append(
                    f'<path d="M {int_x:.1f} {ry:.1f} '
                    f'L {int_x+sdir*ow_px:.1f} {ry:.1f}" '
                    f'stroke="{_DIM}" stroke-width="0.7" stroke-dasharray="4,3" fill="none"/>'
                )
                parts.append(
                    f'<path d="M {int_x+sdir*ow_px:.1f} {ry:.1f} '
                    f'A {ow_px:.1f} {ow_px:.1f} 0 0 {"0" if left_of_plan else "1"} '
                    f'{int_x:.1f} {ry+ow_px:.1f}" '
                    f'stroke="{_DIM}" stroke-width="0.7" stroke-dasharray="4,3" fill="none"/>'
                )

            # Tag badge + size label — placed INSIDE the pod footprint
            # W wall (left_of_plan=True): interior is to the right → offset inward from E face of W wall
            # E wall (left_of_plan=False): interior is to the left → offset inward from W face of E wall
            tag_ofs = 46
            if left_of_plan:
                tx = wall_x + WT + tag_ofs
                lbl_x = tx + 26
            else:
                tx = wall_x - tag_ofs
                lbl_x = tx - 26
            parts.append(_mfr_tag(tx, ry + ow_px/2, tag))
            size_lbl = f"{int(o['width_m']*1000)} × {int(o['height_m']*1000)}"
            parts.append(_t(lbl_x, ry + ow_px/2 + 4, size_lbl, _DS_FONT - 4, "middle", _OPEN_LINE))

            parts.append(_vdim(ry, ry + ow_px, wall_x if left_of_plan else wall_x + WT,
                               f"{int(o['width_m']*1000)}", left_of_plan, level=0))

            gap_mm = int(y_m*1000) if i == 0 else int((y_m - ys_m[i-1] - wo[i-1]["width_m"])*1000)
            if ry - prev_py > 3:
                parts.append(_vdim(prev_py, ry,
                                   wall_x if left_of_plan else wall_x + WT,
                                   str(gap_mm), left_of_plan, level=1))
            prev_py = ry + ow_px

        if wo:
            tail_mm = int((width_m - ys_m[-1] - wo[-1]["width_m"])*1000)
            tail_py = oy + ph - (oy + ys_m[-1]*S + wo[-1]["width_m"]*S)
            if tail_py > 3 and tail_mm > 0:
                parts.append(_vdim(
                    oy + ys_m[-1]*S + wo[-1]["width_m"]*S, oy + ph,
                    wall_x if left_of_plan else wall_x + WT,
                    str(tail_mm), left_of_plan, level=1
                ))

        parts.append(_vdim(oy, oy + ph,
                           wall_x if left_of_plan else wall_x + WT,
                           f"{int(width_m*1000)}", left_of_plan, level=2))

    # ── Roof openings (skylights) ──────────────────────────────────────────────
    rl_n = 0
    for ro in (roof_openings or []):
        if not ro.get("selected", False):
            continue
        rl_n += 1
        rw_m = float(ro.get("width_mm", 600)) / 1000
        rh_m = float(ro.get("height_mm", 900)) / 1000
        rx_off, ry_off = ro.get("x_offset_mm"), ro.get("y_offset_mm")
        ri_w = length_m - 2 * wall_thick_m
        ri_h = width_m  - 2 * wall_thick_m
        rx_m = float(rx_off)/1000 if rx_off not in (None, "") else (ri_w - rw_m) / 2
        ry_m = float(ry_off)/1000 if ry_off not in (None, "") else (ri_h - rh_m) / 2
        rpx  = ix + rx_m * S
        rpy  = iy + ry_m * S
        rw_p, rh_p = rw_m * S, rh_m * S
        parts.append(_r(rpx, rpy, rw_p, rh_p, "#DBEAFE", "#2563EB", 1.2))
        parts.append(
            f'<rect x="{rpx:.1f}" y="{rpy:.1f}" width="{rw_p:.1f}" height="{rh_p:.1f}" '
            f'fill="none" stroke="#2563EB" stroke-width="0.8" stroke-dasharray="5,3"/>'
        )
        parts.append(_mfr_tag(rpx + rw_p/2, rpy + rh_p/2, f"RL{rl_n}"))
        # Rooflight size label
        parts.append(_t(rpx + rw_p/2, rpy - 6,
                        f"{int(rw_m*1000)}×{int(rh_m*1000)}", 7, "middle", "#2563EB"))
        schedule.append((f"RL{rl_n}", "rooflight", int(rw_m*1000), int(rh_m*1000), "Roof/Ceiling"))

    # ── Wall thickness callout ─────────────────────────────────────────────────
    # Small double-headed dim on E wall, placed below centre so it doesn't
    # collide with opening dims
    wt_x  = ox + pw * 0.70
    wt_y1 = oy + ph - WT
    wt_y2 = oy + ph
    wt_str = f"{int(round(wall_thick_m * 1000))} mm"
    parts += [
        _l(wt_x - 6, wt_y1, wt_x + 6, wt_y1, _DIM_RED, _DS_LINE_W),
        _l(wt_x - 6, wt_y2, wt_x + 6, wt_y2, _DIM_RED, _DS_LINE_W),
        _l(wt_x, wt_y1, wt_x, wt_y2, _DIM_RED, _DS_LINE_W),
        _mfr_arrow_v(wt_x, wt_y1, -1),
        _mfr_arrow_v(wt_x, wt_y2, +1),
        _t(wt_x + _DS_ARROW + 4, (wt_y1 + wt_y2)/2 + 5, wt_str, _DS_FONT - 2, "start", _DIM_RED, "bold"),
    ]

    # ── Area annotation (inside room, centred) ─────────────────────────────────
    gross_area    = length_m * width_m
    internal_area = (length_m - 2*wall_thick_m) * (width_m - 2*wall_thick_m)
    name_label    = project_name or pod_name or ""
    if name_label:
        parts.append(_t(cx, cy - 14, name_label, 11, "middle", "#333", "bold"))
    parts.append(_t(cx, cy + (2 if name_label else -6),
                    f"GIA: {gross_area:.1f} m²", 9, "middle", "#555"))
    parts.append(_t(cx, cy + (16 if name_label else 8),
                    f"Internal: {internal_area:.1f} m²", 9, "middle", "#777"))

    # ── Title block ────────────────────────────────────────────────────────────
    # Opening schedule is rendered inside title block col 1 (below drawing title)
    # so it is permanently outside the dimension zone and never clashes.
    # Three columns: [Project + Title + Disclaimer] | [Drawing No + Client ID] | [Cells grid]
    P = 8        # cell padding
    C1W = int(SW * 0.42)
    C2W = int(SW * 0.22)
    C3X = BORD + C1W + C2W
    C3W = SW - BORD - C3X

    # Column dividers
    parts += [
        _l(BORD + C1W, tb_y, BORD + C1W, SH - BORD, "#AAAAAA", 0.7),
        _l(BORD + C1W + C2W, tb_y, BORD + C1W + C2W, SH - BORD, "#AAAAAA", 0.7),
    ]

    # Col 1: Project / Drawing title / Opening Schedule / Disclaimer
    proj_str  = project_name or pod_name or "—"
    title_str = f"Floor Plan  {length_m:.2f}m × {width_m:.2f}m"
    _cell_y = tb_y + P + 7
    parts += [
        _t(BORD + P, _cell_y,      "PROJECT",       6.5, "start", _DIM),
        _t(BORD + P, _cell_y + 11, proj_str,         9,   "start", _LABEL, "bold"),
        _t(BORD + P, _cell_y + 26, "DRAWING TITLE",  6.5, "start", _DIM),
        _t(BORD + P, _cell_y + 37, title_str,        9,   "start", _LABEL, "bold"),
    ]
    # ── Opening schedule — anchored in title block col 1, below drawing title ──
    # This zone is permanently protected: no dimension or drawing element can enter
    # the title block area (everything in the viewport ends at tb_y).
    if schedule:
        TYPE_LABELS = {
            "door": "Ext. Door", "french_door": "Fr. Door",
            "window": "Window", "rooflight": "Rooflight",
        }
        SCH_ROW  = 10   # px per data row
        SCH_COL_W = C1W - 2 * P   # available width in col 1
        sch_x0   = BORD + P
        sch_y0   = _cell_y + 52   # below drawing title value (+37 + 9px font + 6 gap)
        parts.append(_t(sch_x0, sch_y0, "OPENING SCHEDULE", 6.5, "start", _DIM, "bold"))
        sch_y0  += 10
        # 5-column header: REF | TYPE | W mm | H mm | LOCATION
        SCH_COLS = ((0, "REF"), (34, "TYPE"), (108, "W"), (140, "H"), (172, "LOCATION"))
        for dx, lbl in SCH_COLS:
            parts.append(_t(sch_x0 + dx, sch_y0, lbl, 6, "start", _DIM))
        sch_y0 += 2
        parts.append(_l(sch_x0, sch_y0, sch_x0 + SCH_COL_W, sch_y0, _DIM, 0.3))
        sch_y0 += SCH_ROW
        for tag, o_type, w_mm, h_mm, location in schedule:
            ts = TYPE_LABELS.get(o_type, o_type)
            for dx, val in ((0, tag), (34, ts), (108, str(w_mm)), (140, str(h_mm)), (172, location)):
                parts.append(_t(sch_x0 + dx, sch_y0, val, 6.5, "start", _LABEL))
            sch_y0 += SCH_ROW
    if disclaimer:
        disc_y = tb_y + TB_H - 14
        parts.append(_t(BORD + P, disc_y, disclaimer, 6, "start", _DIM))

    # Col 2: Drawing No + Client/Project ID
    c2x0 = BORD + C1W + P
    parts += [
        _t(c2x0, _cell_y,      "DRAWING No.",        6.5, "start", _DIM),
        _t(c2x0, _cell_y + 11, drawing_number or "—", 9,   "start", _LABEL, "bold"),
        _t(c2x0, _cell_y + 28, "CLIENT / PROJECT ID", 6.5, "start", _DIM),
        _t(c2x0, _cell_y + 39, client_project_id or "—", 9, "start", _LABEL, "bold"),
    ]

    # Col 3: 6 cells in a 2×3 grid (Scale, Rev, DrawnBy, CheckedBy, Status, Date)
    half3 = C3W // 2
    ROW_H = TB_H // 3

    def _tb_cell(x, y, label, value, size=8.5):
        parts.append(_t(x, y + 4,  label, 6, "start", _DIM))
        # Clamp value to ~18 chars to avoid overflow
        parts.append(_t(x, y + 15, (value or "—")[:22], size, "start", _LABEL, "bold"))

    rows = [
        (C3X + P,           tb_y,           "SCALE",       scale_str),
        (C3X + P + half3,   tb_y,           "REVISION",    revision),
        (C3X + P,           tb_y + ROW_H,   "DRAWN BY",    drawn_by),
        (C3X + P + half3,   tb_y + ROW_H,   "CHECKED BY",  checked_by),
        (C3X + P,           tb_y + 2*ROW_H, "STATUS",      status),
        (C3X + P + half3,   tb_y + 2*ROW_H, "DATE",        issue_date),
    ]
    # Row dividers inside col 3
    for i in (1, 2):
        parts.append(_l(C3X, tb_y + i*ROW_H, SW - BORD, tb_y + i*ROW_H, "#DDDDDD", 0.5))
    # Col divider down the middle of col 3
    parts.append(_l(C3X + half3, tb_y, C3X + half3, SH - BORD, "#DDDDDD", 0.5))

    for x, y, lbl, val in rows:
        _tb_cell(x, y, lbl, val)

    parts.append("</svg>")
    return "\n".join(parts)


def generate_drawings(
    elements: list[DecomposedElement],
    width_m: float,
    length_m: float,
    wall_height_m: float,
    stud_spacing_mm: int = 600,
    wall_thick_m: float = 0.30,
    pod_name: str = "",
    roof_openings: list[dict] | None = None,
    wall_u_value: float | None = None,
    floor_u_value: float | None = None,
    roof_u_value: float | None = None,
) -> dict[str, str]:
    """
    Generate all five pod drawings.

    Returns
    -------
    Dict with keys: "floor_plan", "wall_N", "wall_S", "wall_E", "wall_W".
    Values are SVG strings ready for embedding or file download.
    """
    opening_elements = [e for e in elements if e.type == "Opening"]

    by_wall: dict[str, list[dict]] = {"N": [], "S": [], "E": [], "W": []}
    all_openings: list[dict] = []
    for oe in opening_elements:
        g = oe.geometry
        d = {
            "wall":          g["wall"],
            "type":          g["type"],
            "width_m":       g["width_m"],
            "height_m":      g["height_m"],
            "sill_height_m": g.get("sill_height_m", 0.0),
            "x_offset_m":    g.get("x_offset_m"),
            "shape":         g.get("shape", "rectangular"),
        }
        by_wall[g["wall"]].append(d)
        all_openings.append(d)

    # N/S walls span length_m (long E-W walls); E/W walls span width_m
    wall_span = {"N": length_m, "S": length_m, "E": width_m, "W": width_m}

    drawings: dict[str, str] = {
        "floor_plan":  floor_plan_svg(
            width_m, length_m, all_openings,
            wall_thick_m=wall_thick_m,
            pod_name=pod_name,
            roof_openings=roof_openings,
            wall_u_value=wall_u_value,
            floor_u_value=floor_u_value,
            roof_u_value=roof_u_value,
        ),
        "sales_sheet": sales_sheet_svg(width_m, length_m, wall_height_m, all_openings),
    }
    for face in ("N", "S", "E", "W"):
        drawings[f"wall_{face}"] = wall_elevation_svg(
            face=face,
            wall_span_m=wall_span[face],
            wall_height_m=wall_height_m,
            openings=by_wall[face],
            stud_spacing_mm=stud_spacing_mm,
        )
    return drawings
