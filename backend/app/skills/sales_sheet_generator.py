"""
Skill: Sales Sheet Generator

Combined A3-landscape SVG:
  - Architectural floor plan (left): wall poche, door swings, window glazing,
    schematic interior layout with furniture, opening dimension labels,
    overall dimension chains
  - Summary / pricing panel (right): model name, pricing tiers,
    customisation notes, GET OFFER call-to-action
  - Process / payment timeline (bottom): 6-stage delivery flow
"""
import math

# ── Page layout ───────────────────────────────────────────────────────────────
SW, SH   = 1440, 980    # total sheet
PW, PH   = 1000, 680    # plan section (left)
PANEL_X  = 1010         # summary panel left edge
TL_Y     = 692          # timeline top edge

WT_EXT = 0.200          # m — external wall thickness (poche)
WT_INT = 0.100          # m — internal partition thickness

# ── Palette ───────────────────────────────────────────────────────────────────
_BG      = "#FFFFFF"
_PLANBG  = "#F8F8F6"
_RULE    = "#E0E0DC"
_WALL    = "#1C1C1C"    # external wall poche
_WALL_I  = "#787878"    # internal partitions
_FLOOR   = "#F5F5EF"    # general floor fill
_BATHFL  = "#EEF4F7"    # bathroom floor
_WIN_G   = "#C5DAE6"    # window glazing fill
_WIN_L   = "#4080A8"    # glazing stroke / sill lines
_FURN    = "#DDD9D2"    # furniture fill
_FURN_L  = "#B0ACA4"    # furniture stroke
_DIM_C   = "#888888"    # dimension lines + text
_OP_LBL  = "#1A5E8A"    # opening label colour
_ROOM_C  = "#999999"    # room label
_PANEL   = "#111827"    # summary panel bg
_P2      = "#1F2937"    # summary card bg
_AMBER   = "#F59E0B"    # accent
_WHITE   = "#FFFFFF"
_LGREY   = "#9CA3AF"
_TL_BG   = "#0A0F1A"    # timeline bg
_TL_CARD = "#1A2336"    # timeline step card
_TL_BDR  = "#2D3D56"    # card border
_TL_ACC  = "#F59E0B"
_FONT    = "Arial, Helvetica, sans-serif"


# ── SVG primitives ────────────────────────────────────────────────────────────

def _r(x, y, w, h, fill, stroke="none", sw=1.0, rx=0) -> str:
    ra = f' rx="{rx}"' if rx else ""
    return (f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{ra}/>')


def _l(x1, y1, x2, y2, stroke, sw=1.0, dash="") -> str:
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
            f'stroke="{stroke}" stroke-width="{sw}"{d}/>')


def _t(x, y, text, size=11, anchor="middle", fill="#1A1A1A",
       weight="normal", rotate=None) -> str:
    rot = (f' transform="rotate({rotate[0]},{rotate[1]:.1f},{rotate[2]:.1f})"'
           if rotate else "")
    return (f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" '
            f'font-family="{_FONT}" font-size="{size}" fill="{fill}" '
            f'font-weight="{weight}"{rot}>{text}</text>')


def _path(d, fill="none", stroke="#333", sw=1.0) -> str:
    return f'<path d="{d}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'


def _circle(cx, cy, r, fill, stroke="none", sw=1.0) -> str:
    return (f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')


def _ellipse(cx, cy, rx, ry, fill, stroke="none", sw=0.7) -> str:
    return (f'<ellipse cx="{cx:.1f}" cy="{cy:.1f}" rx="{rx:.1f}" ry="{ry:.1f}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')


# ── Dimension helpers ─────────────────────────────────────────────────────────

def _mm(m: float) -> str:
    return str(round(m * 1000))


def _dim_h(x1, x2, y_ref, label, below=True) -> str:
    off = 26 if below else -26
    yd  = y_ref + off
    ye  = yd + (7 if below else -7)
    parts = [
        _l(x1, y_ref + (3 if below else -3), x1, ye, _DIM_C, 0.6),
        _l(x2, y_ref + (3 if below else -3), x2, ye, _DIM_C, 0.6),
        _l(x1 + 4, yd, x2 - 4, yd, _DIM_C, 0.6),
    ]
    parts.append(_t((x1 + x2) / 2, yd + (10 if below else -4),
                    label, 8, "middle", _DIM_C))
    return "".join(parts)


def _dim_v(y1, y2, x_ref, label, left=True) -> str:
    off = -26 if left else 26
    xd  = x_ref + off
    xe  = xd + (-7 if left else 7)
    parts = [
        _l(x_ref + (-3 if left else 3), y1, xe, y1, _DIM_C, 0.6),
        _l(x_ref + (-3 if left else 3), y2, xe, y2, _DIM_C, 0.6),
        _l(xd, y1 + 4, xd, y2 - 4, _DIM_C, 0.6),
    ]
    mx, my = xd + (-10 if left else 10), (y1 + y2) / 2
    parts.append(_t(mx, my, label, 8, "middle", _DIM_C, rotate=(-90, mx, my)))
    return "".join(parts)


# ── Plan scale ────────────────────────────────────────────────────────────────

def _plan_scale(length_m: float, width_m: float) -> float:
    avail_w = PW - 160    # room for dim annotations + labels
    avail_h = PH - 160
    return min(avail_w / length_m, avail_h / width_m) * 0.82


# ── Opening position helper ───────────────────────────────────────────────────

def _opening_positions(span_m: float, openings: list[dict]) -> list[float]:
    n = len(openings)
    if n == 0:
        return []
    section = span_m / (n + 1)
    result = []
    for i, o in enumerate(openings):
        xoff = o.get("x_offset_m")
        ow   = o["width_m"]
        if xoff is not None:
            pos = max(0.0, min(float(xoff), span_m - ow))
        else:
            center = (i + 1) * section
            pos = max(0.0, min(center - ow / 2, span_m - ow))
        result.append(round(pos, 4))
    return result


# ── Door swing ────────────────────────────────────────────────────────────────

def _door_ns(face: str, rx: float, wall_y: float, ow: float, wt: float) -> list[str]:
    """Door swing for N or S wall (horizontal in plan). Swings inward."""
    if face == "N":
        hx, hy = rx, wall_y + wt          # hinge: inner-face, left edge
        ax, ay = hx + ow, hy              # door leaf tip (closed = East)
        bx, by = hx, hy + ow              # door leaf tip (open = South)
        sweep  = 1
    else:
        hx, hy = rx, wall_y               # inner face of S wall
        ax, ay = hx + ow, hy
        bx, by = hx, hy - ow             # swing North (inward)
        sweep  = 0
    arc = (f"M {ax:.1f},{ay:.1f} "
           f"A {ow:.1f},{ow:.1f} 0 0 {sweep} {bx:.1f},{by:.1f}")
    leaf = f"M {hx:.1f},{hy:.1f} L {ax:.1f},{ay:.1f}"
    return [_path(arc, "none", _DIM_C, 0.7), _path(leaf, "none", "#444", 1.4)]


def _door_ew(face: str, wall_x: float, ry: float, wt: float, ow: float) -> list[str]:
    """Door swing for E or W wall (vertical in plan). Swings inward."""
    if face == "W":
        hx, hy = wall_x + wt, ry         # inner face, top edge
        ax, ay = hx, hy + ow             # door tip closed (South)
        bx, by = hx + ow, hy            # door tip open (East)
        sweep  = 0
    else:
        hx, hy = wall_x, ry
        ax, ay = hx, hy + ow
        bx, by = hx - ow, hy           # swing West (inward)
        sweep  = 1
    arc = (f"M {ax:.1f},{ay:.1f} "
           f"A {ow:.1f},{ow:.1f} 0 0 {sweep} {bx:.1f},{by:.1f}")
    leaf = f"M {hx:.1f},{hy:.1f} L {ax:.1f},{ay:.1f}"
    return [_path(arc, "none", _DIM_C, 0.7), _path(leaf, "none", "#444", 1.4)]


# ── Window in plan ────────────────────────────────────────────────────────────

def _window_ns(rx: float, wall_y: float, ow: float, wt: float) -> str:
    """Window in N or S wall: glazing fill + two sill lines."""
    mid = wt / 3
    return (
        _r(rx, wall_y, ow, wt, _WIN_G, _WIN_L, 0.8) +
        _l(rx, wall_y + mid, rx + ow, wall_y + mid, _WIN_L, 0.5) +
        _l(rx, wall_y + wt - mid, rx + ow, wall_y + wt - mid, _WIN_L, 0.5)
    )


def _window_ew(wall_x: float, ry: float, wt: float, ow: float) -> str:
    """Window in E or W wall: glazing fill + two sill lines."""
    mid = wt / 3
    return (
        _r(wall_x, ry, wt, ow, _WIN_G, _WIN_L, 0.8) +
        _l(wall_x + mid, ry, wall_x + mid, ry + ow, _WIN_L, 0.5) +
        _l(wall_x + wt - mid, ry, wall_x + wt - mid, ry + ow, _WIN_L, 0.5)
    )


# ── Furniture helpers ─────────────────────────────────────────────────────────

def _sofa(x, y, w, h) -> list[str]:
    """Sofa: filled rect with back strip + cushion dividers."""
    n_cush = max(2, round(w / 55))
    cw = w / n_cush
    parts = [
        _r(x, y, w, h, _FURN, _FURN_L, 0.7),
        _r(x, y, w, h * 0.22, _FURN_L, _FURN_L, 0.4),
    ]
    for i in range(1, n_cush):
        parts.append(_l(x + i * cw, y + 2, x + i * cw, y + h - 2, _FURN_L, 0.5))
    return parts


def _dining_table(cx, cy, w, d) -> list[str]:
    """Dining table + 4 chairs."""
    x, y   = cx - w / 2, cy - d / 2
    ch_d   = max(10, d * 0.28)
    ch_w   = w * 0.38
    gap    = 4
    return [
        _r(x, y, w, d, _FURN, _FURN_L, 0.8),
        _r(x + w * 0.10, y - ch_d - gap, ch_w, ch_d, _FURN, _FURN_L, 0.6),
        _r(x + w * 0.52, y - ch_d - gap, ch_w, ch_d, _FURN, _FURN_L, 0.6),
        _r(x + w * 0.10, y + d + gap,    ch_w, ch_d, _FURN, _FURN_L, 0.6),
        _r(x + w * 0.52, y + d + gap,    ch_w, ch_d, _FURN, _FURN_L, 0.6),
    ]


def _kitchen_l(x, y, long_w, short_h, depth) -> list[str]:
    """L-shaped kitchen counter in NW corner."""
    parts = [
        _r(x, y, long_w, depth, _FURN, _FURN_L, 0.7),
        _r(x, y, depth, short_h, _FURN, _FURN_L, 0.7),
    ]
    # Hob (2×2 circles)
    for i in range(2):
        for j in range(2):
            parts.append(_circle(
                x + depth * 1.8 + i * depth * 0.75,
                y + depth * 0.5 + j * depth * 0.75 - depth * 0.35,
                depth * 0.16, "none", _FURN_L, 0.6))
    # Sink
    sx = x + long_w * 0.62
    parts.append(_r(sx, y + depth * 0.12, depth * 0.88, depth * 0.76, "#E0E8EC", _FURN_L, 0.6))
    return parts


def _bed(x, y, w, h) -> list[str]:
    pw  = w * 0.37
    ph  = h * 0.13
    return [
        _r(x, y, w, h, _FURN, _FURN_L, 0.8),
        _r(x, y, w, h * 0.11, _FURN_L, _FURN_L, 0.5),
        _r(x + 4, y + h * 0.15, pw, ph, "#ECEAE4", _FURN_L, 0.5),
        _r(x + w - 4 - pw, y + h * 0.15, pw, ph, "#ECEAE4", _FURN_L, 0.5),
        _l(x, y + h * 0.31, x + w, y + h * 0.31, _FURN_L, 0.5),
    ]


def _wardrobe(x, y, w, h) -> list[str]:
    return [
        _r(x, y, w, h, _FURN, _FURN_L, 0.8),
        _l(x, y, x + w, y + h, _FURN_L, 0.5, "3,3"),
        _l(x + w, y, x, y + h, _FURN_L, 0.5, "3,3"),
    ]


def _toilet(x, y, w, h) -> list[str]:
    cx, cy = x + w / 2, y + h * 0.35 + h * 0.65 / 2
    return [
        _r(x, y, w, h * 0.35, _FURN, _FURN_L, 0.7),
        _ellipse(cx, cy, w / 2 - 2, h * 0.65 / 2 - 1, _FURN, _FURN_L, 0.7),
    ]


def _basin(x, y, w, h) -> list[str]:
    cx, cy = x + w / 2, y + h / 2
    return [
        _ellipse(cx, cy, w / 2 - 2, h / 2 - 2, _FURN, _FURN_L, 0.7),
        _circle(cx, cy + h * 0.12, w * 0.09, _FURN_L),
    ]


def _shower(x, y, size) -> list[str]:
    cx, cy = x + size / 2, y + size / 2
    r1, r2 = size * 0.18, size * 0.30
    parts  = [_r(x, y, size, size, _FURN, _FURN_L, 0.7)]
    parts.append(_circle(cx, cy, r1, "none", _FURN_L, 0.6))
    for ang in range(0, 360, 45):
        a = math.radians(ang)
        parts.append(_l(cx + r1 * math.cos(a), cy + r1 * math.sin(a),
                        cx + r2 * math.cos(a), cy + r2 * math.sin(a),
                        _FURN_L, 0.5))
    return parts


# ── Floor plan ────────────────────────────────────────────────────────────────

def _floor_plan_elements(
    length_m: float,
    width_m: float,
    openings: list[dict],
    sc: float,
    ox: float,
    oy: float,
) -> list[str]:
    ew = length_m * sc
    ns = width_m * sc
    wt = WT_EXT * sc
    wi = WT_INT * sc

    # Interior bounds
    ix, iy = ox + wt, oy + wt
    iw, ih = ew - 2 * wt, ns - 2 * wt

    # Room zone proportions
    split   = iw * 0.60        # living | bedroom partition (x from ix)
    bath_frac = 0.55           # bedroom | bathroom partition (y fraction of ih)
    bath_y  = iy + ih * bath_frac

    priv_x  = ix + split
    priv_iw = iw - split

    parts: list[str] = []

    # ── Room fills (drawn before wall poche) ─────────────────────────────────
    parts.append(_r(ix, iy, split, ih, _FLOOR, "none"))
    parts.append(_r(priv_x, iy, priv_iw, ih * bath_frac, _FLOOR, "none"))
    parts.append(_r(priv_x, bath_y, priv_iw, ih * (1 - bath_frac), _BATHFL, "none"))

    # ── External wall poche (dark full-building rect, overpaints corners) ────
    parts.append(_r(ox, oy, ew, ns, _WALL, _WALL, 2.5))

    # Re-expose room fills inside the wall
    parts.append(_r(ix, iy, split, ih, _FLOOR, "none"))
    parts.append(_r(priv_x, iy, priv_iw, ih * bath_frac, _FLOOR, "none"))
    parts.append(_r(priv_x, bath_y, priv_iw, ih * (1 - bath_frac), _BATHFL, "none"))

    # ── Internal partitions ───────────────────────────────────────────────────
    # Living / private separator (vertical)
    parts.append(_r(priv_x - wi / 2, iy, wi, ih, _WALL_I, _WALL_I, 0.5))
    # Bedroom / bathroom separator (horizontal)
    parts.append(_r(priv_x - wi / 2, bath_y - wi / 2, priv_iw + wi, wi, _WALL_I, _WALL_I, 0.5))

    # Interior face outline (thin)
    parts.append(_r(ix, iy, iw, ih, "none", "#666666", 0.4))

    # ── Openings ─────────────────────────────────────────────────────────────
    by_wall: dict[str, list[dict]] = {"N": [], "S": [], "E": [], "W": []}
    for o in openings:
        w = o.get("wall", "")
        if w in by_wall:
            by_wall[w].append(o)

    # Assign sequential labels: D1, D2… W1, W2…
    dc, wc = 0, 0
    label_map: dict[int, str] = {}
    for face in ("N", "S", "E", "W"):
        for o in by_wall[face]:
            otype = o.get("type", "window").lower()
            if otype in ("door",):
                dc += 1; label_map[id(o)] = f"D{dc}"
            elif otype in ("vent", "rooflight"):
                label_map[id(o)] = "V"
            else:
                wc += 1; label_map[id(o)] = f"W{wc}"

    def _size(o):
        return f"{_mm(o['width_m'])}×{_mm(o['height_m'])}"

    # N wall
    n_pos = _opening_positions(length_m, by_wall["N"])
    for o, x_m in zip(by_wall["N"], n_pos):
        ow_px = o["width_m"] * sc
        rx = ox + x_m * sc
        parts.append(_r(rx, oy, ow_px, wt, _FLOOR, "none"))
        if o.get("type", "").lower() == "door":
            parts.extend(_door_ns("N", rx, oy, ow_px, wt))
        else:
            parts.append(_window_ns(rx, oy, ow_px, wt))
        lbl = label_map[id(o)]
        parts.append(_t(rx + ow_px / 2, oy - 22, f"{lbl}",
                        7, "middle", _OP_LBL, "bold"))
        parts.append(_t(rx + ow_px / 2, oy - 12, _size(o),
                        6, "middle", _OP_LBL))

    # S wall
    s_top = oy + ns - wt
    s_pos = _opening_positions(length_m, by_wall["S"])
    for o, x_m in zip(by_wall["S"], s_pos):
        ow_px = o["width_m"] * sc
        rx = ox + x_m * sc
        parts.append(_r(rx, s_top, ow_px, wt, _FLOOR, "none"))
        if o.get("type", "").lower() == "door":
            parts.extend(_door_ns("S", rx, s_top, ow_px, wt))
        else:
            parts.append(_window_ns(rx, s_top, ow_px, wt))
        lbl = label_map[id(o)]
        parts.append(_t(rx + ow_px / 2, s_top + wt + 14, f"{lbl}",
                        7, "middle", _OP_LBL, "bold"))
        parts.append(_t(rx + ow_px / 2, s_top + wt + 24, _size(o),
                        6, "middle", _OP_LBL))

    # W wall
    w_pos = _opening_positions(width_m, by_wall["W"])
    for o, y_m in zip(by_wall["W"], w_pos):
        ow_px = o["width_m"] * sc
        ry = oy + y_m * sc
        parts.append(_r(ox, ry, wt, ow_px, _FLOOR, "none"))
        if o.get("type", "").lower() == "door":
            parts.extend(_door_ew("W", ox, ry, wt, ow_px))
        else:
            parts.append(_window_ew(ox, ry, wt, ow_px))
        lbl = label_map[id(o)]
        parts.append(_t(ox - 6, ry + ow_px / 2 - 5,
                        f"{lbl}", 7, "end", _OP_LBL, "bold"))
        parts.append(_t(ox - 6, ry + ow_px / 2 + 6,
                        _size(o), 6, "end", _OP_LBL))

    # E wall
    e_left = ox + ew - wt
    e_pos  = _opening_positions(width_m, by_wall["E"])
    for o, y_m in zip(by_wall["E"], e_pos):
        ow_px = o["width_m"] * sc
        ry = oy + y_m * sc
        parts.append(_r(e_left, ry, wt, ow_px, _FLOOR, "none"))
        if o.get("type", "").lower() == "door":
            parts.extend(_door_ew("E", e_left, ry, wt, ow_px))
        else:
            parts.append(_window_ew(e_left, ry, wt, ow_px))
        lbl = label_map[id(o)]
        parts.append(_t(e_left + wt + 6, ry + ow_px / 2 - 5,
                        f"{lbl}", 7, "start", _OP_LBL, "bold"))
        parts.append(_t(e_left + wt + 6, ry + ow_px / 2 + 6,
                        _size(o), 6, "start", _OP_LBL))

    # ── Furniture ─────────────────────────────────────────────────────────────
    # Living / kitchen zone: (ix, iy) → (ix + split, iy + ih)
    lw, lh = split, ih

    # Kitchen L-counter (NW corner of living zone)
    k_dep  = min(0.62 * sc, lh * 0.16)
    k_long = min(lw * 0.55, 2.8 * sc)
    k_sh   = min(lh * 0.48, 2.4 * sc)
    parts.extend(_kitchen_l(ix, iy, k_long, k_sh, k_dep))

    # Dining table (centre of living zone)
    dt_w = min(1.2 * sc, lw * 0.38)
    dt_d = min(0.75 * sc, lh * 0.22)
    dt_cx = ix + lw * 0.62
    dt_cy = iy + lh * 0.40
    parts.extend(_dining_table(dt_cx, dt_cy, dt_w, dt_d))

    # Sofa (south side of living zone)
    sf_w = min(2.0 * sc, lw * 0.68)
    sf_d = min(0.85 * sc, lh * 0.18)
    sf_x = ix + (lw - sf_w) / 2
    sf_y = iy + lh - sf_d - 2
    parts.extend(_sofa(sf_x, sf_y, sf_w, sf_d))

    # ── Bedroom ───────────────────────────────────────────────────────────────
    bx  = priv_x + wi * 0.6
    bw  = priv_iw - wi * 0.6
    bh  = ih * bath_frac

    bed_w = min(1.55 * sc, bw * 0.85)
    bed_h = min(2.05 * sc, bh * 0.72)
    bed_x = bx + (bw - bed_w) / 2
    bed_y = iy + (bh - bed_h) / 2
    parts.extend(_bed(bed_x, bed_y, bed_w, bed_h))

    ward_h = min(0.60 * sc, bh * 0.20)
    parts.extend(_wardrobe(bx, iy, bw * 0.88, ward_h))

    # ── Bathroom ──────────────────────────────────────────────────────────────
    bax  = priv_x + wi * 0.6
    baw  = priv_iw - wi * 0.6
    bay  = bath_y + wi * 0.6
    bah  = ih * (1 - bath_frac) - wi * 0.6

    sh_sz = min(0.95 * sc, min(baw, bah) * 0.60)
    parts.extend(_shower(bax + baw - sh_sz, bay, sh_sz))

    bas_w = min(0.55 * sc, baw * 0.52)
    bas_h = min(0.44 * sc, bah * 0.32)
    parts.extend(_basin(bax, bay, bas_w, bas_h))

    tl_w = min(0.50 * sc, baw * 0.48)
    tl_h = min(0.70 * sc, bah * 0.50)
    parts.extend(_toilet(bax, bay + bah - tl_h, tl_w, tl_h))

    # ── Room labels ───────────────────────────────────────────────────────────
    lbl_kw = max(6, min(8, int(sc * 0.08)))
    parts += [
        _t(ix + lw * 0.68, sf_y - 8, "LIVING",   lbl_kw, "middle", _ROOM_C),
        _t(ix + k_dep * 1.5, iy + k_sh * 0.55, "KITCHEN",
           lbl_kw - 1, "middle", _ROOM_C, rotate=(-90, ix + k_dep * 1.5, iy + k_sh * 0.55)),
        _t(bx + bw / 2, bed_y + bed_h + 12, "BEDROOM", lbl_kw, "middle", _ROOM_C),
        _t(bax + baw / 2, bay + bah / 2,    "BATH",    lbl_kw, "middle", _ROOM_C),
    ]

    # ── Overall dimensions ────────────────────────────────────────────────────
    parts.append(_dim_h(ox, ox + ew, oy + ns, f"{_mm(length_m)}", below=True))
    parts.append(_dim_v(oy, oy + ns, ox, f"{_mm(width_m)}", left=True))

    # ── North arrow ───────────────────────────────────────────────────────────
    na_x = ox + ew + 42
    na_y = oy + 36
    parts += [
        _l(na_x, na_y, na_x, na_y - 22, "#555", 1.5),
        _path(f"M {na_x:.1f},{na_y-22:.1f} L {na_x-6:.1f},{na_y-8:.1f} "
              f"L {na_x+6:.1f},{na_y-8:.1f} Z", "#555", "#555"),
        _t(na_x, na_y + 12, "N", 9, "middle", "#555", "bold"),
    ]

    return parts


# ── Summary panel ─────────────────────────────────────────────────────────────

def _summary_panel(config: dict) -> list[str]:
    x  = PANEL_X
    w  = SW - PANEL_X
    h  = PH

    model       = config.get("model_name",      "Pod Studio")
    full_price  = config.get("full_mode_price",  "POA")
    int_price   = config.get("interior_price",   "—")
    ext_price   = config.get("exterior_price",   "—")
    total       = config.get("total_price",      "POA")
    notes       = config.get("notes", [
        "Kitchen: Dark Grey",
        "Floor: Clear White",
        "Facade: Black Stained",
    ])

    parts = [_r(x, 0, w, h, _PANEL, "none")]

    # Header stripe
    parts.append(_r(x, 0, w, 52, _P2, "none"))
    parts.append(_t(x + w / 2, 32, "SUMMARY", 10, "middle", _AMBER, "bold"))
    parts.append(_l(x, 52, x + w, 52, "#2D3748", 0.8))

    # Model name
    parts.append(_t(x + 20, 78, model, 14, "start", _WHITE, "bold"))
    parts.append(_l(x + 20, 86, x + w - 20, 86, "#2D3748", 0.5))

    # Full mode price
    yl = 110
    parts.append(_t(x + 20, yl, "FULL MODE", 8, "start", _LGREY))
    parts.append(_t(x + w - 20, yl, full_price, 17, "end", _AMBER, "bold"))
    parts.append(_l(x + 20, yl + 14, x + w - 20, yl + 14, "#2D3748", 0.5))

    # Breakdown
    yl += 36
    for label, val in [("INTERIOR", int_price), ("EXTERIOR", ext_price)]:
        parts.append(_t(x + 20, yl, label, 8, "start", _LGREY))
        parts.append(_t(x + w - 20, yl, val, 10, "end", _WHITE))
        yl += 26

    parts.append(_l(x + 20, yl, x + w - 20, yl, "#2D3748", 0.7))
    yl += 22

    # Total
    parts.append(_t(x + 20, yl, "TOTAL", 9, "start", _LGREY))
    parts.append(_t(x + w - 20, yl, total, 15, "end", _AMBER, "bold"))
    yl += 28
    parts.append(_l(x + 20, yl, x + w - 20, yl, "#2D3748", 0.5))
    yl += 22

    # Customisation notes
    parts.append(_t(x + 20, yl, "SPECIFICATION", 7, "start", "#4B5563"))
    yl += 18
    for note in notes:
        parts.append(_t(x + 20, yl, f"— {note}", 8, "start", _WHITE))
        yl += 17

    # GET OFFER button
    btn_y = h - 58
    bx    = x + 20
    bw_   = w - 40
    parts += [
        _r(bx, btn_y, bw_, 38, _AMBER, "none", 0, 7),
        _t(bx + bw_ / 2, btn_y + 24, "GET OFFER", 11, "middle", "#111827", "bold"),
    ]

    return parts


# ── Timeline ──────────────────────────────────────────────────────────────────

def _timeline() -> list[str]:
    y  = TL_Y
    h  = SH - TL_Y

    steps = [
        ("RESERVE",          "ONLINE",      ["Customer support", "will contact you"]),
        ("10%",              "",             ["Reservation deposit", "AR drawings permit"]),
        ("40%",              "",             ["Signing contract", "Start of production"]),
        ("12–16 WEEKS",      "PRODUCTION",  ["Manufacturing time"]),
        ("30%",              "",             ["4 weeks prior shipping", "Confirming transport"]),
        ("20%",              "",             ["Final payment", "Releasing shipment"]),
    ]
    n        = len(steps)
    pad_h    = 30
    card_gap = 10
    total_w  = SW - 2 * pad_h
    card_w   = (total_w - card_gap * (n - 1)) / n
    card_h   = h - 40
    card_y   = y + 20

    parts = [
        _r(0, y, SW, h, _TL_BG, "none"),
        _l(0, y, SW, y, "#1E293B", 1.0),
    ]

    for i, (title, sub, notes) in enumerate(steps):
        cx = pad_h + i * (card_w + card_gap)
        parts.append(_r(cx, card_y, card_w, card_h, _TL_CARD, _TL_BDR, 0.8, 8))

        # Step number dot
        dot_x = cx + 16
        dot_y = card_y + 18
        parts.append(_circle(dot_x, dot_y, 7, _TL_ACC))
        parts.append(_t(dot_x, dot_y + 4, str(i + 1), 7, "middle", "#111827", "bold"))

        # Title
        parts.append(_t(cx + card_w / 2, card_y + 36, title,
                        14 if len(title) <= 4 else 11, "middle", _TL_ACC, "bold"))
        if sub:
            parts.append(_t(cx + card_w / 2, card_y + 52, sub,
                            7, "middle", _LGREY))

        # Notes
        ny = card_y + (62 if sub else 54)
        for note in notes:
            parts.append(_t(cx + card_w / 2, ny, note, 7.5, "middle", _WHITE))
            ny += 14

        # Connector arrow (between cards)
        if i < n - 1:
            ax = cx + card_w + card_gap / 2
            ay = card_y + card_h / 2
            parts.append(_t(ax, ay + 5, "›", 18, "middle", _TL_BDR))

    return parts


# ── Public entry point ────────────────────────────────────────────────────────

def sales_sheet_svg(
    width_m: float,
    length_m: float,
    wall_height_m: float,
    openings: list[dict],
    config: dict | None = None,
) -> str:
    """
    Generate a combined sales-sheet SVG.

    Parameters
    ----------
    width_m         Pod short dimension (N–S)
    length_m        Pod long dimension (E–W, drawn horizontally)
    wall_height_m   Eaves height (used in annotations only)
    openings        Same format as drawing_generator — list of dicts with wall,
                    type, width_m, height_m, sill_height_m, x_offset_m
    config          Optional pricing / customisation dict:
                    model_name, full_mode_price, interior_price,
                    exterior_price, total_price, notes (list[str])
    """
    sc = _plan_scale(length_m, width_m)
    ew = length_m * sc
    ns = width_m * sc

    # Centre plan within plan section, shifted slightly upward
    ox = (PW - ew) / 2
    oy = (PH - ns) / 2 - 8

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {SW} {SH}">',
        _r(0, 0, SW, SH, _BG, "none"),
        _r(0, 0, PW, PH, _PLANBG, "none"),
    ]

    # Plan section header
    parts.append(_t(PW / 2, oy - 34,
                    f"FLOOR PLAN  —  {length_m:.1f} × {width_m:.1f} m  "
                    f"(wall height {wall_height_m:.1f} m)",
                    9, "middle", "#AAAAAA"))

    # Scale indicator
    sc_bar_m  = 1.0
    sc_bar_px = sc_bar_m * sc
    sc_x = ox
    sc_y = oy + ns + 52
    parts += [
        _l(sc_x, sc_y, sc_x + sc_bar_px, sc_y, "#888", 1.5),
        _l(sc_x, sc_y - 4, sc_x, sc_y + 4, "#888", 1.0),
        _l(sc_x + sc_bar_px, sc_y - 4, sc_x + sc_bar_px, sc_y + 4, "#888", 1.0),
        _t(sc_x + sc_bar_px / 2, sc_y + 12, "1 m", 7, "middle", "#888"),
    ]

    # Dividers
    parts.append(_l(PW, 0, PW, PH, _RULE, 1.0))
    parts.append(_l(0, TL_Y, SW, TL_Y, _RULE, 1.0))

    # Floor plan
    parts.extend(_floor_plan_elements(length_m, width_m, openings, sc, ox, oy))

    # Summary panel
    parts.extend(_summary_panel(config or {}))

    # Timeline
    parts.extend(_timeline())

    parts.append("</svg>")
    return "\n".join(parts)
