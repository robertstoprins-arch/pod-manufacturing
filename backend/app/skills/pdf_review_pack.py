"""
Manufacturer / Internal Technical Pack PDF Generator
Produces a 10-page A4 PDF for manufacturer and internal technical review.
"""
from __future__ import annotations

import io
import math
from datetime import date, datetime, timezone
from dataclasses import dataclass, field
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.platypus import (
    BaseDocTemplate, Frame, PageTemplate, Paragraph, Spacer,
    Table, TableStyle, HRFlowable, KeepTogether,
)
from reportlab.platypus import Flowable
from reportlab.graphics.shapes import Drawing, Rect, Line, String, Group
from reportlab.graphics import renderPDF

# ── Colour palette ─────────────────────────────────────────────────────────────

INK      = colors.HexColor("#1a1a1a")
INK2     = colors.HexColor("#444444")
MUTED    = colors.HexColor("#888888")
RULE     = colors.HexColor("#e0e0e0")
RULE2    = colors.HexColor("#cccccc")
BG_ALT   = colors.HexColor("#f7f7f7")
BG_HEAD  = colors.HexColor("#eeeeee")
ACCENT   = colors.HexColor("#1a1a1a")
C_GREEN  = colors.HexColor("#16a34a")
C_AMBER  = colors.HexColor("#d97706")
C_RED    = colors.HexColor("#dc2626")
C_BLUE   = colors.HexColor("#2563eb")
BG_GREEN = colors.HexColor("#f0fdf4")
BG_AMBER = colors.HexColor("#fffbeb")
BG_RED   = colors.HexColor("#fef2f2")

PW, PH = A4          # 595.3 × 841.9 pt
ML = MR = 18 * mm    # margins
MT = MB = 20 * mm
CW = PW - ML - MR    # content width ≈ 159 mm

# ── Style helpers ──────────────────────────────────────────────────────────────

def _styles():
    ss = getSampleStyleSheet()
    def s(name, **kw):
        return ParagraphStyle(name, **kw)

    return {
        "h1":       s("h1",      fontName="Helvetica-Bold",   fontSize=18, textColor=INK,  leading=22, spaceAfter=4),
        "h2":       s("h2",      fontName="Helvetica-Bold",   fontSize=12, textColor=INK,  leading=15, spaceAfter=4, spaceBefore=14),
        "h3":       s("h3",      fontName="Helvetica-Bold",   fontSize=9,  textColor=INK,  leading=12, spaceAfter=3, spaceBefore=8),
        "body":     s("body",    fontName="Helvetica",        fontSize=8,  textColor=INK2, leading=12, spaceAfter=2),
        "small":    s("small",   fontName="Helvetica",        fontSize=7,  textColor=MUTED, leading=10),
        "label":    s("label",   fontName="Helvetica-Bold",   fontSize=7,  textColor=MUTED, leading=9,  spaceAfter=1),
        "note":     s("note",    fontName="Helvetica-Oblique",fontSize=7,  textColor=MUTED, leading=10, spaceAfter=2),
        "warn":     s("warn",    fontName="Helvetica-Oblique",fontSize=7,  textColor=C_AMBER, leading=10),
        "cover_title":  s("cover_title",  fontName="Helvetica-Bold",   fontSize=28, textColor=INK,  leading=34, spaceAfter=6),
        "cover_sub":    s("cover_sub",    fontName="Helvetica",        fontSize=11, textColor=INK2, leading=15, spaceAfter=4),
        "cover_status": s("cover_status", fontName="Helvetica-Bold",   fontSize=9,  textColor=MUTED, leading=12, spaceAfter=2),
        "tbl_head": s("tbl_head", fontName="Helvetica-Bold",  fontSize=7,  textColor=INK2, leading=9),
        "tbl_cell": s("tbl_cell", fontName="Helvetica",       fontSize=7,  textColor=INK2, leading=9),
        "tbl_mono": s("tbl_mono", fontName="Courier",         fontSize=6.5,textColor=INK2, leading=9),
        "miss":     s("miss",     fontName="Helvetica-Oblique",fontSize=7, textColor=C_AMBER, leading=9),
        "timeline": s("timeline", fontName="Helvetica",       fontSize=8,  textColor=INK2, leading=11, spaceAfter=1),
        "disc":     s("disc",     fontName="Helvetica",       fontSize=7.5,textColor=INK2, leading=12, spaceAfter=3),
    }


def _tbl_style(has_header=True, row_alt=True, col_widths=None):
    cmds = [
        ("FONTNAME",    (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE",    (0, 0), (-1, -1), 7),
        ("TOPPADDING",  (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING",(0,0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING",(0, 0), (-1, -1), 4),
        ("LINEBELOW",   (0, 0), (-1, -1), 0.3, RULE),
        ("VALIGN",      (0, 0), (-1, -1), "TOP"),
        ("WORDWRAP",    (0, 0), (-1, -1), True),
    ]
    if has_header:
        cmds += [
            ("BACKGROUND",  (0, 0), (-1, 0), BG_HEAD),
            ("FONTNAME",    (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",    (0, 0), (-1, 0), 7),
            ("TEXTCOLOR",   (0, 0), (-1, 0), INK2),
            ("LINEBELOW",   (0, 0), (-1, 0), 0.6, RULE2),
        ]
    if row_alt:
        cmds.append(("ROWBACKGROUNDS", (0, 1 if has_header else 0), (-1, -1), [colors.white, BG_ALT]))
    return TableStyle(cmds)


def P(text, style, **kw):
    return Paragraph(str(text) if text is not None else "", style, **kw)


def fmtN(v, dec=2):
    if v is None:
        return "—"
    return f"{v:,.{dec}f}"


def fmtCost(v, currency="EUR"):
    if v is None:
        return "—"
    sym = {"EUR": "€", "USD": "$", "GBP": "£"}.get(currency, currency + " ")
    return f"{sym}{v:,.0f}"


# ── Plan drawing ───────────────────────────────────────────────────────────────

def _plan_drawing(
    geom: dict,
    wall_thick_mm: float,
    draw_w: float,
    draw_h: float,
    pod_name: str = "",
    wall_u_value: float | None = None,
    floor_u_value: float | None = None,
    roof_u_value: float | None = None,
) -> Drawing:
    """Generate a top-down architectural plan as a reportlab Drawing."""
    import math as _math
    ext_w_m = float(geom.get("width_m", 6.0))
    ext_l_m = float(geom.get("length_m", 9.0))
    wt_m    = (wall_thick_mm or 300) / 1000.0

    # Reserve right margin for U-value panel if we have U-values
    u_panel_w = 50 if any(v is not None for v in (wall_u_value, floor_u_value, roof_u_value)) else 0

    pad = 28  # pt padding around the plan
    avail_w = draw_w - 2 * pad - u_panel_w
    avail_h = draw_h - 2 * pad
    scale   = min(avail_w / ext_w_m, avail_h / ext_l_m)

    # Drawing origin: bottom-left of the pod external footprint
    ox = pad + (avail_w - ext_w_m * scale) / 2
    oy = pad + (avail_h - ext_l_m * scale) / 2

    d = Drawing(draw_w, draw_h)

    wt = wt_m * scale   # wall thickness in pt

    def sx(m): return ox + m * scale
    def sy(m): return oy + m * scale

    ew = ext_w_m * scale
    el = ext_l_m * scale

    wall_fill  = colors.HexColor("#d8d8d8")
    inner_fill = colors.HexColor("#f8f8f8")

    # Outer wall rect
    d.add(Rect(sx(0), sy(0), ew, el, fillColor=wall_fill, strokeColor=INK, strokeWidth=0.8))
    # Inner void
    d.add(Rect(sx(0)+wt, sy(0)+wt, ew-2*wt, el-2*wt, fillColor=inner_fill, strokeColor=INK, strokeWidth=0.5))

    # Room centre annotation: pod name + floor area
    int_w_m = ext_w_m - 2 * wt_m
    int_l_m = ext_l_m - 2 * wt_m
    floor_area = int_w_m * int_l_m
    cx = sx(0) + ew / 2
    cy = sy(0) + el / 2
    if pod_name:
        d.add(String(cx, cy + 6, pod_name, fontName="Helvetica-Bold", fontSize=7,
                     fillColor=INK2, textAnchor="middle"))
    d.add(String(cx, cy - 4, f"{floor_area:.1f} m²", fontName="Helvetica", fontSize=6.5,
                 fillColor=MUTED, textAnchor="middle"))

    # Wall thickness annotation (double-headed arrow on E wall)
    wt_ax = sx(ext_w_m) + 6
    wt_ay_bot = sy(0) + el/2 - wt/2
    wt_ay_top = sy(0) + el/2 + wt/2
    d.add(Line(wt_ax, wt_ay_bot, wt_ax, wt_ay_top, strokeColor=MUTED, strokeWidth=0.8))
    d.add(Line(wt_ax-2, wt_ay_bot+2, wt_ax, wt_ay_bot, strokeColor=MUTED, strokeWidth=0.8))
    d.add(Line(wt_ax+2, wt_ay_bot+2, wt_ax, wt_ay_bot, strokeColor=MUTED, strokeWidth=0.8))
    d.add(Line(wt_ax-2, wt_ay_top-2, wt_ax, wt_ay_top, strokeColor=MUTED, strokeWidth=0.8))
    d.add(Line(wt_ax+2, wt_ay_top-2, wt_ax, wt_ay_top, strokeColor=MUTED, strokeWidth=0.8))
    d.add(String(wt_ax + 4, (wt_ay_bot + wt_ay_top)/2 - 2,
                 f"{int(wall_thick_mm)}mm", fontName="Helvetica", fontSize=5,
                 fillColor=MUTED, textAnchor="start"))

    # Openings
    openings = geom.get("openings", [])
    opening_labels: list[dict] = []
    door_count = window_count = french_count = 0
    # Track offset dim levels per wall edge to avoid overlap
    dim_levels: dict[str, int] = {"S": 0, "N": 0, "E": 0, "W": 0}

    for o in openings:
        o_type    = o.get("type", "window")
        o_wall    = o.get("wall", "S")
        o_width_m = float(o.get("width_m", 1.0))
        o_h_m     = float(o.get("height_m", 1.0))
        x_off_m   = o.get("x_offset_m")
        x_off_m   = float(x_off_m) if (x_off_m is not None and x_off_m != "") else None

        if o_type == "door":
            door_count += 1
            label_code = f"D{door_count}"
        elif o_type == "french_door":
            french_count += 1
            label_code = f"FD{french_count}"
        else:
            window_count += 1
            label_code = f"W{window_count}"

        ow = o_width_m * scale

        if o_wall in ("S", "N"):
            if x_off_m is not None:
                pos = x_off_m * scale
            else:
                pos = (ew - ow) / 2
            if o_wall == "S":
                rx = sx(0) + pos
                ry = sy(0)
                rw, rh = ow, wt
            else:
                rx = sx(0) + pos
                ry = sy(ext_l_m) - wt
                rw, rh = ow, wt
        else:
            if x_off_m is not None:
                pos = x_off_m * scale
            else:
                pos = (el - ow) / 2
            if o_wall == "W":
                rx = sx(0)
                ry = sy(0) + pos
                rw, rh = wt, ow
            else:
                rx = sx(ext_w_m) - wt
                ry = sy(0) + pos
                rw, rh = wt, ow

        # Cut opening (white rect over wall)
        d.add(Rect(rx, ry, rw, rh, fillColor=inner_fill, strokeColor=colors.white, strokeWidth=0))

        # Opening line
        if o_wall in ("S", "N"):
            d.add(Line(rx, ry + rh/2, rx + rw, ry + rh/2, strokeColor=INK, strokeWidth=1.5))
        else:
            d.add(Line(rx + rw/2, ry, rx + rw/2, ry + rh, strokeColor=INK, strokeWidth=1.5))

        # Door swing — door leaf (solid) + dashed radius line to arc endpoint
        if o_type in ("door", "french_door"):
            import math as _m
            swing_r = ow
            dk = dict(strokeColor=INK2, strokeWidth=0.5)
            dd = dict(strokeColor=INK2, strokeWidth=0.5, strokeDashArray=[2, 2])
            if o_wall == "S":
                hinge_x, hinge_y = rx, ry
                d.add(Line(hinge_x, hinge_y, hinge_x + swing_r, hinge_y, **dk))
                d.add(Line(hinge_x, hinge_y, hinge_x, hinge_y - swing_r, **dd))
                d.add(Line(hinge_x + swing_r, hinge_y, hinge_x, hinge_y - swing_r, **dd))
            elif o_wall == "N":
                hinge_x, hinge_y = rx, ry + wt
                d.add(Line(hinge_x, hinge_y, hinge_x + swing_r, hinge_y, **dk))
                d.add(Line(hinge_x, hinge_y, hinge_x, hinge_y + swing_r, **dd))
                d.add(Line(hinge_x + swing_r, hinge_y, hinge_x, hinge_y + swing_r, **dd))
            elif o_wall == "W":
                hinge_x, hinge_y = rx, ry
                d.add(Line(hinge_x, hinge_y, hinge_x, hinge_y + swing_r, **dk))
                d.add(Line(hinge_x, hinge_y, hinge_x - swing_r, hinge_y, **dd))
                d.add(Line(hinge_x, hinge_y + swing_r, hinge_x - swing_r, hinge_y, **dd))
            else:  # E
                hinge_x, hinge_y = rx + wt, ry
                d.add(Line(hinge_x, hinge_y, hinge_x, hinge_y + swing_r, **dk))
                d.add(Line(hinge_x, hinge_y, hinge_x + swing_r, hinge_y, **dd))
                d.add(Line(hinge_x, hinge_y + swing_r, hinge_x + swing_r, hinge_y, **dd))

        # Opening label
        lx = rx + rw / 2
        ly = ry + rh / 2
        d.add(String(lx, ly + 3, label_code, fontName="Helvetica-Bold", fontSize=5.5,
                     fillColor=INK, textAnchor="middle"))
        # Size label offset from wall
        size_lbl = f"{int(o_width_m*1000)}×{int(o_h_m*1000)}"
        if o_wall == "S":
            d.add(String(lx, ry - 6, size_lbl, fontName="Helvetica", fontSize=4.5,
                         fillColor=MUTED, textAnchor="middle"))
        elif o_wall == "N":
            d.add(String(lx, ry + rh + 3, size_lbl, fontName="Helvetica", fontSize=4.5,
                         fillColor=MUTED, textAnchor="middle"))
        elif o_wall == "W":
            d.add(String(rx - 4, ly, size_lbl, fontName="Helvetica", fontSize=4.5,
                         fillColor=MUTED, textAnchor="end"))
        else:  # E
            d.add(String(rx + rw + 4, ly, size_lbl, fontName="Helvetica", fontSize=4.5,
                         fillColor=MUTED, textAnchor="start"))

        # Offset dimension (from nearest corner to opening edge)
        if x_off_m is not None:
            lvl = dim_levels[o_wall]
            dim_levels[o_wall] += 1
            off_gap = 8 + lvl * 10
            if o_wall == "S":
                y_dim = sy(0) - off_gap - 6
                d.add(Line(sx(0), sy(0), sx(0), y_dim, strokeColor=MUTED, strokeWidth=0.4))
                d.add(Line(rx, sy(0), rx, y_dim, strokeColor=MUTED, strokeWidth=0.4))
                d.add(Line(sx(0), y_dim, rx, y_dim, strokeColor=MUTED, strokeWidth=0.5))
                d.add(String((sx(0)+rx)/2, y_dim - 6, f"{int(x_off_m*1000)}mm",
                             fontName="Helvetica", fontSize=4.5, fillColor=MUTED, textAnchor="middle"))
            elif o_wall == "N":
                y_dim = sy(ext_l_m) + off_gap + 4
                d.add(Line(sx(0), sy(ext_l_m), sx(0), y_dim, strokeColor=MUTED, strokeWidth=0.4))
                d.add(Line(rx, sy(ext_l_m), rx, y_dim, strokeColor=MUTED, strokeWidth=0.4))
                d.add(Line(sx(0), y_dim, rx, y_dim, strokeColor=MUTED, strokeWidth=0.5))
                d.add(String((sx(0)+rx)/2, y_dim + 3, f"{int(x_off_m*1000)}mm",
                             fontName="Helvetica", fontSize=4.5, fillColor=MUTED, textAnchor="middle"))
            elif o_wall == "W":
                x_dim = sx(0) - off_gap - 6
                d.add(Line(sx(0), sy(0), x_dim, sy(0), strokeColor=MUTED, strokeWidth=0.4))
                d.add(Line(sx(0), ry, x_dim, ry, strokeColor=MUTED, strokeWidth=0.4))
                d.add(Line(x_dim, sy(0), x_dim, ry, strokeColor=MUTED, strokeWidth=0.5))
                d.add(String(x_dim - 3, (sy(0)+ry)/2, f"{int(x_off_m*1000)}mm",
                             fontName="Helvetica", fontSize=4.5, fillColor=MUTED, textAnchor="end"))
            else:  # E
                x_dim = sx(ext_w_m) + off_gap + 6
                d.add(Line(sx(ext_w_m), sy(0), x_dim, sy(0), strokeColor=MUTED, strokeWidth=0.4))
                d.add(Line(sx(ext_w_m), ry, x_dim, ry, strokeColor=MUTED, strokeWidth=0.4))
                d.add(Line(x_dim, sy(0), x_dim, ry, strokeColor=MUTED, strokeWidth=0.5))
                d.add(String(x_dim + 3, (sy(0)+ry)/2, f"{int(x_off_m*1000)}mm",
                             fontName="Helvetica", fontSize=4.5, fillColor=MUTED, textAnchor="start"))

        w_mm = int(o_width_m * 1000)
        h_mm = int(o_h_m * 1000)
        opening_labels.append({
            "code": label_code,
            "type": o_type.replace("_", " ").title(),
            "size": f"{w_mm}×{h_mm}",
        })

    # Roof openings (skylights) — shown as dashed rectangle in plan
    rl_count = 0
    for ro in geom.get("roof_openings", []):
        if not ro.get("selected", False):
            continue
        rl_count += 1
        rw_m = float(ro.get("width_mm", 600)) / 1000
        rl_m = float(ro.get("height_mm", 900)) / 1000
        rx_off = ro.get("x_offset_mm")
        ry_off = ro.get("y_offset_mm")
        rx_m = float(rx_off) / 1000 if rx_off not in (None, "") else (ext_w_m - rw_m) / 2
        ry_m = float(ry_off) / 1000 if ry_off not in (None, "") else (ext_l_m - rl_m) / 2
        d.add(Rect(sx(rx_m), sy(ry_m), rw_m * scale, rl_m * scale,
                   fillColor=colors.HexColor("#dbeafe"),
                   strokeColor=C_BLUE, strokeWidth=0.7, strokeDashArray=[3, 2]))
        rlabel = f"RL{rl_count}"
        d.add(String(sx(rx_m) + rw_m*scale/2, sy(ry_m) + rl_m*scale/2 + 2,
                     rlabel, fontName="Helvetica-Bold", fontSize=5.5,
                     fillColor=C_BLUE, textAnchor="middle"))
        # Size label
        d.add(String(sx(rx_m) + rw_m*scale/2, sy(ry_m) - 5,
                     f"{int(rw_m*1000)}×{int(rl_m*1000)}",
                     fontName="Helvetica", fontSize=4.5, fillColor=C_BLUE, textAnchor="middle"))
        w_mm = int(rw_m * 1000)
        h_mm = int(rl_m * 1000)
        opening_labels.append({"code": rlabel, "type": "Rooflight / Skylight", "size": f"{w_mm}×{h_mm}"})

    # Compass N arrow (top-right of plan)
    nx, ny = sx(0) + ew + 20, sy(0) + el - 10
    d.add(Line(nx, ny - 10, nx, ny + 10, strokeColor=INK, strokeWidth=1.2))
    d.add(Line(nx, ny + 10, nx - 3, ny + 4, strokeColor=INK, strokeWidth=1.2))
    d.add(Line(nx, ny + 10, nx + 3, ny + 4, strokeColor=INK, strokeWidth=1.2))
    d.add(String(nx, ny + 12, "N", fontName="Helvetica-Bold", fontSize=7, fillColor=INK, textAnchor="middle"))

    # Overall dimension lines
    def dim_h(x1, x2, y_base, text):
        off = 12
        yd = y_base - off
        d.add(Line(x1, y_base, x1, yd - 2, strokeColor=MUTED, strokeWidth=0.4))
        d.add(Line(x2, y_base, x2, yd - 2, strokeColor=MUTED, strokeWidth=0.4))
        d.add(Line(x1, yd, x2, yd, strokeColor=MUTED, strokeWidth=0.5))
        d.add(String((x1+x2)/2, yd - 7, text, fontName="Helvetica", fontSize=5.5,
                     fillColor=MUTED, textAnchor="middle"))

    def dim_v(y1, y2, x_base, text):
        off = 12
        xd = x_base - off
        d.add(Line(x_base, y1, xd - 2, y1, strokeColor=MUTED, strokeWidth=0.4))
        d.add(Line(x_base, y2, xd - 2, y2, strokeColor=MUTED, strokeWidth=0.4))
        d.add(Line(xd, y1, xd, y2, strokeColor=MUTED, strokeWidth=0.5))
        mid = (y1 + y2) / 2
        d.add(String(xd - 4, mid - 2, text, fontName="Helvetica", fontSize=5.5,
                     fillColor=MUTED, textAnchor="end"))

    dim_h(sx(0), sx(ext_w_m), sy(0), f"{ext_w_m:.1f} m")
    dim_v(sy(0), sy(ext_l_m), sx(0), f"{ext_l_m:.1f} m")

    # U-value panel (right of drawing)
    if u_panel_w:
        upx = sx(0) + ew + u_panel_w * 0.05
        upy = sy(0) + el
        row_h = 14
        uv_rows = []
        if wall_u_value  is not None: uv_rows.append(("Wall",  f"{wall_u_value:.3f}"))
        if floor_u_value is not None: uv_rows.append(("Floor", f"{floor_u_value:.3f}"))
        if roof_u_value  is not None: uv_rows.append(("Roof",  f"{roof_u_value:.3f}"))
        panel_h = row_h * len(uv_rows) + 20
        d.add(Rect(upx, upy - panel_h, u_panel_w * 0.9, panel_h,
                   fillColor=colors.HexColor("#f0f4ff"),
                   strokeColor=colors.HexColor("#c7d2fe"), strokeWidth=0.5))
        d.add(String(upx + u_panel_w * 0.45, upy - 10, "U-values",
                     fontName="Helvetica-Bold", fontSize=5.5, fillColor=INK2, textAnchor="middle"))
        for i, (lbl, val) in enumerate(uv_rows):
            ry_ = upy - 20 - i * row_h
            d.add(String(upx + 4, ry_, lbl + ":", fontName="Helvetica", fontSize=5.5,
                         fillColor=MUTED, textAnchor="start"))
            d.add(String(upx + u_panel_w * 0.85, ry_, val,
                         fontName="Helvetica-Bold", fontSize=5.5, fillColor=INK, textAnchor="end"))
            d.add(String(upx + u_panel_w * 0.88, ry_, " W/m²K",
                         fontName="Helvetica", fontSize=4.5, fillColor=MUTED, textAnchor="start"))

    return d, opening_labels


# ── Build-up colour map (layer role → fill colour for the strip preview) ──────

ROLE_COLOUR = {
    "internal_finish": colors.HexColor("#f5f0eb"),
    "service_void":    colors.HexColor("#fef9c3"),
    "vcl":             colors.HexColor("#bfdbfe"),
    "sheathing":       colors.HexColor("#d1d5db"),
    "framing_zone":    colors.HexColor("#f3e8ff"),
    "insulation":      colors.HexColor("#bbf7d0"),
    "breather":        colors.HexColor("#cffafe"),
    "cavity":          colors.HexColor("#e5e7eb"),
    "cladding":        colors.HexColor("#fed7aa"),
    "structure":       colors.HexColor("#d1d5db"),
    "external_finish": colors.HexColor("#c7d2fe"),
}
ROLE_DEFAULT = colors.HexColor("#f0f0f0")


def _buildup_strip(layers: list[dict], width: float, height: float = 28) -> Drawing:
    """Horizontal bar showing layers inside → outside with thickness proportional widths."""
    total_mm = sum(l["thickness_mm"] for l in layers) or 1
    d = Drawing(width, height)
    x = 0
    for l in layers:
        pct = l["thickness_mm"] / total_mm
        w = width * pct
        fill = ROLE_COLOUR.get(l.get("role", ""), ROLE_DEFAULT)
        d.add(Rect(x, 4, w, height - 8, fillColor=fill, strokeColor=RULE2, strokeWidth=0.4))
        if w > 12:
            d.add(String(x + w/2, height/2 - 2, str(int(l["thickness_mm"])),
                         fontName="Helvetica", fontSize=5, fillColor=INK2, textAnchor="middle"))
        x += w
    # Labels
    d.add(String(0, 0, "Inside", fontName="Helvetica-Oblique", fontSize=5, fillColor=MUTED, textAnchor="start"))
    d.add(String(width, 0, "Outside", fontName="Helvetica-Oblique", fontSize=5, fillColor=MUTED, textAnchor="end"))
    return d


# ── Data collection ────────────────────────────────────────────────────────────

@dataclass
class ReviewPackData:
    spec_id: int
    spec_name: str
    revision: str
    project_name: str
    generated_at: datetime
    geometry: dict
    # Build-ups
    wall_bu: dict | None = None   # {name, element_type, layers[], result}
    floor_bu: dict | None = None
    roof_bu: dict | None = None
    # BOM
    bom_lines: list[dict] = field(default_factory=list)
    bom_areas: dict = field(default_factory=dict)
    bom_opening_counts: dict = field(default_factory=dict)
    bom_total: float | None = None
    # Evidence
    materials: list[dict] = field(default_factory=list)
    # Provisional allowances
    allowances: list[dict] = field(default_factory=list)
    # Package selections from frontend
    packages: dict = field(default_factory=dict)
    pkg_overrides: dict = field(default_factory=dict)
    # Finish catalogue selections (from /finish-cost endpoint)
    finish_lines: list[dict] = field(default_factory=list)
    finish_total: float = 0.0
    # Selling price settings
    markup_percent: float = 50.0
    vat_rate_percent: float = 21.0
    round_to_nearest: int = 100


def _resolve_buildup(bu, db) -> dict | None:
    if bu is None:
        return None
    from app.skills.build_up_resolver import ResolverLayer, resolve
    layers_out = []
    resolver_layers = []
    for layer in sorted(bu.layers, key=lambda l: l.position_order):
        from app.models import MaterialLibrary
        mat = db.get(MaterialLibrary, layer.material_id)
        if mat is None:
            continue
        props = layer.properties or {}
        role = props.get("role", "")
        inc = props.get("include_in_u_value", True)
        layers_out.append({
            "position_order": layer.position_order,
            "name": mat.name,
            "supplier_ref": mat.supplier_ref or "",
            "role": role,
            "thickness_mm": layer.thickness_mm,
            "lambda_W_mK": mat.lambda_W_mK,
            "include_in_u_value": inc,
        })
        resolver_layers.append(ResolverLayer(
            name=mat.name,
            thickness_mm=layer.thickness_mm,
            lambda_W_mK=mat.lambda_W_mK or 0.0,
            role=role,
            include_in_u_value=inc,
            framing_fraction=float(props.get("framing_fraction", 0.15)),
        ))

    result = resolve(resolver_layers, bu.element_type or "ExternalWall")
    return {
        "name": bu.name,
        "element_type": bu.element_type,
        "build_up_type": bu.build_up_type,
        "total_thickness_mm": result.total_thickness_mm,
        "u_value": result.u_value,
        "r_total": result.r_total,
        "errors": result.errors,
        "warnings": result.warnings,
        "targets": [
            {"code": t.code, "label": t.label, "target_u_value": t.target_u_value,
             "passes": t.passes, "headroom": t.headroom}
            for t in result.targets
        ],
        "assumptions": result.assumptions,
        "layers": layers_out,
    }


# ── Package cost helpers (mirrors CostSummary.jsx logic) ──────────────────────

PACKAGE_GROUPS = [
    {"id": "roof_finish",  "label": "Roof Finish",               "type": "bool",  "options": [
        {"code": "roof_epdm_standard", "name": "EPDM Roof Finish", "low": 700, "high": 700},
    ]},
    {"id": "heating",      "label": "Heating",                   "type": "radio", "options": [
        {"code": "electric_radiators_base",  "name": "Electric Radiators — Base",    "low": 250,  "high": 600},
        {"code": "electric_radiators_smart", "name": "Smart Electric Radiators",     "low": 700,  "high": 1400},
        {"code": "air_to_air_heat_pump",     "name": "Air-to-Air Heat Pump",         "low": 1500, "high": 3000},
    ]},
    {"id": "ventilation",  "label": "Ventilation",               "type": "multi", "options": [
        {"code": "trickle_vents_allowance",  "name": "Trickle Vents",               "low": 80,   "high": 200},
        {"code": "bathroom_extract",         "name": "Bathroom Extract Fan",         "low": 120,  "high": 300},
        {"code": "kitchen_extract",          "name": "Kitchen Extract Provision",    "low": 200,  "high": 600},
        {"code": "mvhr_premium",             "name": "MVHR Premium Option",          "low": 1500, "high": 3000},
    ]},
    {"id": "cctv_data",    "label": "CCTV / Data",               "type": "multi", "options": [
        {"code": "cctv_cat6_prewire",        "name": "CAT6 Prewire",                "low": 350,  "high": 800},
        {"code": "basic_4_camera_ip",        "name": "Basic 4-Camera IP Package",   "low": 800,  "high": 2000},
    ]},
    {"id": "pv_ready",     "label": "PV-Ready Provision",        "type": "bool",  "options": [
        {"code": "pv_ready_roof",            "name": "PV-Ready Roof Provision",     "low": 250,  "high": 600},
    ]},
    {"id": "finishes",     "label": "Interior Finishes",         "type": "radio", "options": [
        {"code": "budget_finishes",          "name": "Budget Internal Finishes",    "low": 2500, "high": 4000},
        {"code": "standard_finishes",        "name": "Standard Internal Finishes",  "low": 4500, "high": 7000},
    ]},
    {"id": "furniture",    "label": "Furniture / Client Items",  "type": "qty",   "options": [
        {"code": "kitchenette",              "name": "Kitchenette Allowance",       "low": 600,  "high": 600},
        {"code": "single_bed",              "name": "Single Bed",                  "low": 270,  "high": 270},
        {"code": "double_bed",              "name": "Double Bed",                  "low": 370,  "high": 370},
        {"code": "office_desk",             "name": "Office Desk + Chair",         "low": 370,  "high": 370},
        {"code": "vanity_unit",             "name": "Vanity Unit Allowance",       "low": 150,  "high": 150},
    ]},
    {"id": "groundworks",  "label": "Concrete / Groundworks",    "type": "radio", "options": [
        {"code": "basic_groundworks_pkg",    "name": "Basic Groundworks Package",   "low": 2000, "high": 5000},
    ]},
]
_PKG_BY_CODE = {o["code"]: {**o, "group_id": g["id"], "group_label": g["label"]}
                for g in PACKAGE_GROUPS for o in g["options"]}


def _active_pkg_lines(packages: dict, overrides: dict) -> list[dict]:
    """Return list of {group_label, name, code, qty, low, high} for selected packages."""
    lines = []
    for g in PACKAGE_GROUPS:
        gid = g["id"]
        gtype = g["type"]
        opts_by_code = {o["code"]: o for o in g["options"]}

        if gtype == "bool":
            if packages.get(gid):
                opt = g["options"][0]
                ov = overrides.get(opt["code"], {})
                lines.append({
                    "group_label": g["label"], "name": opt["name"], "code": opt["code"],
                    "qty": 1, "low": ov.get("low", opt["low"]), "high": ov.get("high", opt["high"]),
                })
        elif gtype == "radio":
            code = packages.get(gid)
            if code and code in opts_by_code:
                opt = opts_by_code[code]
                ov = overrides.get(code, {})
                lines.append({
                    "group_label": g["label"], "name": opt["name"], "code": code,
                    "qty": 1, "low": ov.get("low", opt["low"]), "high": ov.get("high", opt["high"]),
                })
        elif gtype == "multi":
            for code in (packages.get(gid) or []):
                if code in opts_by_code:
                    opt = opts_by_code[code]
                    ov = overrides.get(code, {})
                    lines.append({
                        "group_label": g["label"], "name": opt["name"], "code": code,
                        "qty": 1, "low": ov.get("low", opt["low"]), "high": ov.get("high", opt["high"]),
                    })
        elif gtype == "qty":
            fm = packages.get(gid) or {}
            for opt in g["options"]:
                qty = fm.get(opt["code"], 0)
                if qty and qty > 0:
                    ov = overrides.get(opt["code"], {})
                    lines.append({
                        "group_label": g["label"], "name": opt["name"], "code": opt["code"],
                        "qty": qty,
                        "low":  (ov.get("low", opt["low"]) or 0) * qty,
                        "high": (ov.get("high", opt["high"]) or 0) * qty,
                    })
    return lines


# ── PDF generator ──────────────────────────────────────────────────────────────

class ReviewPackPDF:
    def __init__(self, data: ReviewPackData):
        self.d = data
        self.S = _styles()
        self.buf = io.BytesIO()
        self._page_num = 0
        self._total_pages = 0

    def _header_footer(self, canvas, doc):
        canvas.saveState()
        self._page_num += 1
        pn = self._page_num

        # Top rule
        canvas.setStrokeColor(RULE2)
        canvas.setLineWidth(0.5)
        canvas.line(ML, PH - MT + 8, PW - MR, PH - MT + 8)

        # Header: project name left, pack title right
        canvas.setFont("Helvetica", 6.5)
        canvas.setFillColor(MUTED)
        canvas.drawString(ML, PH - MT + 11, self.d.project_name.upper())
        canvas.drawRightString(PW - MR, PH - MT + 11, "MANUFACTURER / INTERNAL TECHNICAL PACK")

        # Bottom rule
        canvas.line(ML, MB - 8, PW - MR, MB - 8)
        # Footer
        canvas.drawString(ML, MB - 15, f"Generated: {self.d.generated_at.strftime('%d %b %Y')}")
        canvas.drawString(ML + 60*mm, MB - 15, f"Revision: {self.d.revision}")
        canvas.drawString(ML + 120*mm, MB - 15, "Status: FOR REVIEW")
        canvas.drawRightString(PW - MR, MB - 15, f"Page {pn}")
        canvas.restoreState()

    def _section(self, title: str, subtitle: str = "") -> list:
        els = []
        els.append(HRFlowable(width=CW, thickness=1.2, color=INK, spaceAfter=4))
        els.append(P(title, self.S["h2"]))
        if subtitle:
            els.append(P(subtitle, self.S["note"]))
        return els

    # ── Page 1: Cover ──────────────────────────────────────────────────────────

    def _cover(self) -> list:
        S = self.S
        d = self.d
        geom = d.geometry
        floor_m2 = float(geom.get("width_m", 0)) * float(geom.get("length_m", 0))

        els = []
        els.append(Spacer(1, 30 * mm))
        els.append(P("TOP-R SOLUTIONS", S["cover_status"]))
        els.append(Spacer(1, 4 * mm))
        els.append(P(d.project_name, S["cover_title"]))
        els.append(Spacer(1, 2 * mm))
        els.append(P(d.spec_name, S["cover_sub"]))
        els.append(Spacer(1, 6 * mm))
        els.append(HRFlowable(width=CW, thickness=2, color=INK, spaceAfter=6))

        # Status block
        status_data = [
            ["STATUS", "REVISION", "DATE"],
            ["FOR REVIEW", d.revision, d.generated_at.strftime("%d %b %Y")],
        ]
        st_tbl = Table(status_data, colWidths=[CW/3]*3)
        st_tbl.setStyle(TableStyle([
            ("FONTNAME",    (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",    (0, 0), (-1, 0), 7),
            ("TEXTCOLOR",   (0, 0), (-1, 0), MUTED),
            ("FONTNAME",    (0, 1), (-1, 1), "Helvetica-Bold"),
            ("FONTSIZE",    (0, 1), (-1, 1), 13),
            ("TEXTCOLOR",   (0, 1), (-1, 1), INK),
            ("TOPPADDING",  (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING",(0,0), (-1, -1), 6),
            ("LINEBELOW",   (0, 0), (-1, 0), 0.3, RULE),
            ("ALIGN",       (0, 0), (-1, -1), "LEFT"),
        ]))
        els.append(st_tbl)
        els.append(Spacer(1, 8 * mm))

        # Key metrics grid
        w_bu = d.wall_bu
        f_bu = d.floor_bu
        r_bu = d.roof_bu
        metrics = [
            ["EXTERNAL DIMENSIONS",
             f"{geom.get('width_m', '—')} m W × {geom.get('length_m', '—')} m L × {geom.get('wall_height_m', '—')} m H"],
            ["GROSS FLOOR AREA",     f"{floor_m2:.1f} m²"],
            ["WALL BUILD-UP",        w_bu["name"] if w_bu else "Not assigned"],
            ["FLOOR BUILD-UP",       f_bu["name"] if f_bu else "Not assigned"],
            ["ROOF BUILD-UP",        r_bu["name"] if r_bu else "Not assigned"],
            ["WALL U-VALUE",         f"{w_bu['u_value']:.3f} W/m²K" if w_bu and w_bu["u_value"] else "—"],
            ["FLOOR U-VALUE",        f"{f_bu['u_value']:.3f} W/m²K" if f_bu and f_bu["u_value"] else "—"],
            ["ROOF U-VALUE",         f"{r_bu['u_value']:.3f} W/m²K" if r_bu and r_bu["u_value"] else "—"],
        ]
        m_tbl = Table(metrics, colWidths=[55*mm, CW - 55*mm])
        m_tbl.setStyle(TableStyle([
            ("FONTNAME",    (0, 0), (0, -1), "Helvetica-Bold"),
            ("FONTSIZE",    (0, 0), (-1,-1), 7.5),
            ("TEXTCOLOR",   (0, 0), (0, -1), MUTED),
            ("TEXTCOLOR",   (1, 0), (1, -1), INK),
            ("FONTNAME",    (1, 0), (1, -1), "Helvetica"),
            ("TOPPADDING",  (0, 0), (-1,-1), 3),
            ("BOTTOMPADDING",(0,0), (-1,-1), 3),
            ("LINEBELOW",   (0, 0), (-1,-1), 0.3, RULE),
            ("VALIGN",      (0, 0), (-1,-1), "TOP"),
        ]))
        els.append(m_tbl)
        els.append(Spacer(1, 10 * mm))

        # Disclaimer banner
        disc = ("Manufacturer / Internal Technical Pack. Preliminary information only. "
                "Professional review required before manufacture, installation, or statutory submission.")
        disc_tbl = Table([[P(disc, S["note"])]], colWidths=[CW])
        disc_tbl.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), BG_ALT),
            ("BOX",           (0, 0), (-1, -1), 0.5, RULE2),
            ("TOPPADDING",    (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("LEFTPADDING",   (0, 0), (-1, -1), 10),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 10),
        ]))
        els.append(disc_tbl)
        return els

    # ── Page 2: Executive Summary ──────────────────────────────────────────────

    def _summary(self) -> list:
        S = self.S
        d = self.d
        geom = d.geometry
        floor_m2 = float(geom.get("width_m", 0)) * float(geom.get("length_m", 0))
        els = []
        els += self._section("Executive Summary", "Preliminary cost and performance overview")

        # Dimensions + U-values side by side
        dims = [
            [P("Dimension", S["tbl_head"]), P("Value", S["tbl_head"])],
            ["Width",       f"{geom.get('width_m', '—')} m"],
            ["Length",      f"{geom.get('length_m', '—')} m"],
            ["Wall height", f"{geom.get('wall_height_m', '—')} m"],
            ["Floor area",  f"{floor_m2:.1f} m²"],
        ]
        w_bu, f_bu, r_bu = d.wall_bu, d.floor_bu, d.roof_bu
        uvals = [
            [P("Element", S["tbl_head"]), P("U-value W/m²K", S["tbl_head"]), P("Thickness mm", S["tbl_head"]), P("Target pass", S["tbl_head"])],
        ]
        for bu, label in [(w_bu, "External Wall"), (f_bu, "Floor"), (r_bu, "Roof")]:
            if bu:
                target_str = "—"
                if bu["targets"]:
                    t = bu["targets"][0]
                    target_str = ("PASS" if t["passes"] else "REVIEW") + f" ≤{t['target_u_value']}"
                uvals.append([label, f"{bu['u_value']:.3f}", f"{bu['total_thickness_mm']:.0f}", target_str])
            else:
                uvals.append([label, "—", "—", "—"])

        dim_tbl = Table([[P("Pod Dimensions", S["h3"])]], colWidths=[CW])
        dim_tbl.setStyle(TableStyle([("BOTTOMPADDING", (0,0),(-1,-1), 2)]))
        els.append(dim_tbl)

        col_w = [CW * 0.4, CW * 0.6]
        inner_dims = Table(dims[1:], colWidths=col_w)
        inner_dims.setStyle(_tbl_style(has_header=False))
        els.append(inner_dims)
        els.append(Spacer(1, 4*mm))

        uv_tbl = Table(uvals, colWidths=[CW*0.3, CW*0.2, CW*0.25, CW*0.25])
        uv_tbl.setStyle(_tbl_style())
        els.append(P("Thermal Performance", S["h3"]))
        els.append(uv_tbl)
        els.append(Spacer(1, 4*mm))

        # Cost groups
        els.append(P("Indicative Cost Summary", S["h3"]))
        els.append(P("Prices are provisional allowances only and remain editable in the app.", S["note"]))

        bom_lines = d.bom_lines
        pkg_lines = _active_pkg_lines(d.packages, d.pkg_overrides)

        # Group BOM by rough cost category
        GROUP_MAP = {
            "internal_finish": "Envelope / Shell",
            "service_void":    "Envelope / Shell",
            "vcl":             "Envelope / Shell",
            "sheathing":       "Envelope / Shell",
            "framing_zone":    "Envelope / Shell",
            "framing_zone_timber": "Envelope / Shell",
            "framing_zone_pir":    "Envelope / Shell",
            "insulation":      "Envelope / Shell",
            "breather":        "Envelope / Shell",
            "cavity":          "Envelope / Shell",
            "cladding":        "Envelope / Shell",
            "structure":       "Concrete / Groundworks",
            "opening":         "Envelope / Shell",
        }
        group_totals: dict[str, tuple[float, float]] = {}  # group → (low, high)

        for l in bom_lines:
            if l.get("line_cost") is None:
                continue
            grp = GROUP_MAP.get(l.get("role", ""), "Other")
            lo, hi = group_totals.get(grp, (0, 0))
            cost = l["line_cost"]
            group_totals[grp] = (lo + cost, hi + cost)

        # Add package groups
        PKG_PHASE_GROUP = {
            "Roof Finish":             "Roof Finish",
            "Heating":                 "Heating + Ventilation",
            "Ventilation":             "Heating + Ventilation",
            "CCTV / Data":             "CCTV / Data",
            "PV-Ready Provision":      "PV-Ready Provision",
            "Interior Finishes":       "Finishes",
            "Furniture / Client Items":"Furniture / Client Discretion",
            "Concrete / Groundworks":  "Concrete / Groundworks",
        }
        for pl in pkg_lines:
            grp = PKG_PHASE_GROUP.get(pl["group_label"], pl["group_label"])
            lo, hi = group_totals.get(grp, (0, 0))
            group_totals[grp] = (lo + (pl["low"] or 0), hi + (pl["high"] or 0))

        cost_rows = [[
            P("Cost Group", S["tbl_head"]),
            P("Low €", S["tbl_head"]),
            P("High €", S["tbl_head"]),
        ]]
        total_low = total_high = 0
        ORDER = ["Envelope / Shell", "Concrete / Groundworks", "Roof Finish",
                 "Heating + Ventilation", "Finishes", "Furniture / Client Discretion",
                 "CCTV / Data", "PV-Ready Provision", "Other"]
        for grp in ORDER:
            if grp in group_totals:
                lo, hi = group_totals[grp]
                cost_rows.append([grp, fmtCost(lo), fmtCost(hi)])
                total_low += lo; total_high += hi

        cost_rows.append([P("TOTAL (indicative)", S["tbl_head"]),
                          P(fmtCost(total_low), S["tbl_head"]),
                          P(fmtCost(total_high), S["tbl_head"])])

        c_tbl = Table(cost_rows, colWidths=[CW*0.55, CW*0.225, CW*0.225])
        c_tbl.setStyle(_tbl_style())
        # Bold last row
        c_tbl.setStyle(TableStyle([
            ("FONTNAME",   (0, -1), (-1, -1), "Helvetica-Bold"),
            ("BACKGROUND", (0, -1), (-1, -1), BG_HEAD),
            ("LINEABOVE",  (0, -1), (-1, -1), 0.8, RULE2),
        ]))
        els.append(c_tbl)

        # Selling price breakdown (manufacturer / internal view)
        els.append(Spacer(1, 5*mm))
        els.append(P("Selling Price Calculation", S["h3"]))
        els.append(P("Internal use only — not for client distribution.", S["warn"]))

        mid_cost = (total_low + total_high) / 2
        mp   = d.markup_percent
        vp   = d.vat_rate_percent
        rtn  = d.round_to_nearest
        markup_amt  = round(mid_cost * mp / 100, 2)
        ex_vat      = round(mid_cost + markup_amt, 2)
        vat_amt     = round(ex_vat * vp / 100, 2)
        inc_vat     = round(ex_vat + vat_amt, 2)
        rounded     = math.ceil(inc_vat / rtn) * rtn if rtn > 0 else inc_vat

        sp_rows = [
            [P("Item", S["tbl_head"]), P("Amount €", S["tbl_head"])],
            ["Internal cost (mid estimate)", fmtCost(mid_cost)],
            [f"Markup ({mp:.1f}%)", f"+ {fmtCost(markup_amt)}"],
            ["Selling price ex VAT", fmtCost(ex_vat)],
            [f"VAT ({vp:.1f}%)", f"+ {fmtCost(vat_amt)}"],
            ["Selling price inc VAT", fmtCost(inc_vat)],
        ]
        if rtn > 0:
            sp_rows.append([P(f"Rounded (to €{rtn})", S["tbl_head"]),
                            P(fmtCost(rounded), S["tbl_head"])])

        sp_tbl = Table(sp_rows, colWidths=[CW * 0.7, CW * 0.3])
        sp_tbl.setStyle(_tbl_style())
        sp_tbl.setStyle(TableStyle([
            ("FONTNAME",   (0, -1), (-1, -1), "Helvetica-Bold"),
            ("BACKGROUND", (0, -1), (-1, -1), BG_AMBER),
            ("TEXTCOLOR",  (0, -1), (-1, -1), C_AMBER),
            ("LINEABOVE",  (0, -1), (-1, -1), 0.8, RULE2),
        ]))
        els.append(sp_tbl)
        return els

    # ── Page 3: Plan ───────────────────────────────────────────────────────────

    def _plan_page(self) -> list:
        S = self.S
        d = self.d
        geom = d.geometry
        wall_thick = d.wall_bu["total_thickness_mm"] if d.wall_bu else 300

        els = []
        els += self._section("Architectural Plan", "Top-down floor plan — preliminary, for review only")

        wall_uv  = d.wall_bu["u_value"]  if d.wall_bu  else None
        floor_uv = d.floor_bu["u_value"] if d.floor_bu else None
        roof_uv  = d.roof_bu["u_value"]  if d.roof_bu  else None
        drawing, opening_labels = _plan_drawing(
            geom, wall_thick, CW, 150 * mm,
            pod_name=d.spec_name,
            wall_u_value=wall_uv if wall_uv else None,
            floor_u_value=floor_uv if floor_uv else None,
            roof_u_value=roof_uv if roof_uv else None,
        )
        els.append(drawing)
        els.append(Spacer(1, 3 * mm))

        if opening_labels:
            els.append(P("Opening Schedule", S["h3"]))
            rows = [[P("Ref", S["tbl_head"]), P("Type", S["tbl_head"]), P("Size (mm)", S["tbl_head"])]]
            for ol in opening_labels:
                rows.append([ol["code"], ol["type"], ol["size"]])
            op_tbl = Table(rows, colWidths=[20*mm, 80*mm, CW - 100*mm])
            op_tbl.setStyle(_tbl_style())
            els.append(op_tbl)

        els.append(Spacer(1, 3*mm))
        els.append(P(
            "Plan drawing is generated from parametric configuration. "
            "Dimensions are indicative. Door swing directions, set-out dimensions and "
            "opening positions require verification by architect before permit application.",
            S["note"]
        ))
        return els

    # ── Page 4: Build-Up Schedule ──────────────────────────────────────────────

    def _buildup_page(self) -> list:
        S = self.S
        els = []
        els += self._section("Build-Up Schedule", "Layer by layer — inside to outside")

        for bu, label in [(self.d.wall_bu, "External Wall"), (self.d.floor_bu, "Floor"), (self.d.roof_bu, "Roof")]:
            if bu is None:
                els.append(P(f"{label}: Not assigned", S["note"]))
                continue

            els.append(P(f"{label} — {bu['name']}", S["h3"]))

            # Strip preview
            if bu["layers"]:
                strip = _buildup_strip(bu["layers"], CW, 28)
                els.append(strip)
                els.append(Spacer(1, 2*mm))

            # Key metrics
            meta = [
                [P("Total thickness", S["tbl_head"]), P("U-value", S["tbl_head"]), P("R-total", S["tbl_head"])],
                [f"{bu['total_thickness_mm']:.0f} mm",
                 f"{bu['u_value']:.3f} W/m²K" if bu['u_value'] else "—",
                 f"{bu['r_total']:.3f} m²K/W" if bu['r_total'] else "—"],
            ]
            meta_tbl = Table(meta, colWidths=[CW/3]*3)
            meta_tbl.setStyle(_tbl_style())
            els.append(meta_tbl)
            els.append(Spacer(1, 2*mm))

            # Layer table
            rows = [[
                P("#", S["tbl_head"]), P("Layer", S["tbl_head"]),
                P("Role", S["tbl_head"]), P("mm", S["tbl_head"]),
                P("λ W/mK", S["tbl_head"]), P("In U?", S["tbl_head"]),
                P("Supplier ref", S["tbl_head"]),
            ]]
            for l in bu["layers"]:
                lam = f"{l['lambda_W_mK']:.3f}" if l["lambda_W_mK"] else "—"
                rows.append([
                    str(l["position_order"]),
                    P(l["name"], S["tbl_cell"]),
                    P(l["role"], S["tbl_cell"]),
                    str(int(l["thickness_mm"])),
                    lam,
                    "Yes" if l["include_in_u_value"] else "No",
                    P(l["supplier_ref"] or "—", S["tbl_mono"]),
                ])
            layer_tbl = Table(rows, colWidths=[8*mm, 55*mm, 28*mm, 13*mm, 18*mm, 14*mm, CW-136*mm])
            layer_tbl.setStyle(_tbl_style())
            els.append(layer_tbl)
            els.append(Spacer(1, 4*mm))

        return els

    # ── Page 5: Thermal Performance ────────────────────────────────────────────

    def _thermal_page(self) -> list:
        S = self.S
        els = []
        els += self._section("Thermal Performance Summary", "Profile target checks — not compliance certification")

        uv_rows = [[
            P("Element", S["tbl_head"]), P("U-value W/m²K", S["tbl_head"]),
            P("Target", S["tbl_head"]), P("Standard", S["tbl_head"]),
            P("Result", S["tbl_head"]),
        ]]
        for bu, label in [(self.d.wall_bu, "External Wall"), (self.d.floor_bu, "Floor"), (self.d.roof_bu, "Roof")]:
            if bu is None:
                uv_rows.append([label, "—", "—", "—", P("Not assigned", S["miss"])])
                continue
            targets = bu.get("targets") or []
            # Deduplicate targets: if all have the same target_u_value keep only distinct ones
            seen = set()
            unique_targets = []
            for t in targets:
                key = (t.get("target_u_value"), t.get("code", ""))
                if key not in seen:
                    seen.add(key)
                    unique_targets.append(t)
            if not unique_targets:
                unique_targets = [{"code": "—", "label": "—", "target_u_value": None, "passes": None}]

            for i, t in enumerate(unique_targets):
                tgt = f"≤ {t.get('target_u_value')}" if t.get("target_u_value") else "—"
                std = t.get("label") or t.get("code") or "—"
                if t.get("passes") is True:
                    res = P("PASS", ParagraphStyle("pass", fontName="Helvetica-Bold", fontSize=7, textColor=C_GREEN, leading=9))
                elif t.get("passes") is False:
                    res = P("REVIEW / UPGRADE", ParagraphStyle("fail", fontName="Helvetica-Bold", fontSize=6.5, textColor=C_AMBER, leading=9))
                else:
                    res = P("—", S["tbl_cell"])
                # Show element label only on first row for this element
                row_label = label if i == 0 else ""
                uv_rows.append([row_label, f"{bu['u_value']:.3f}" if i == 0 else "", tgt, std, res])
        uv_tbl = Table(uv_rows, colWidths=[CW*0.20, CW*0.14, CW*0.10, CW*0.40, CW*0.16])
        uv_tbl.setStyle(_tbl_style())
        els.append(uv_tbl)
        els.append(Spacer(1, 4*mm))

        # Warnings
        all_warnings = []
        for bu, label in [(self.d.wall_bu, "Wall"), (self.d.floor_bu, "Floor"), (self.d.roof_bu, "Roof")]:
            if bu:
                for w in bu["warnings"]:
                    all_warnings.append(f"{label}: {w}")
        if all_warnings:
            els.append(P("Warnings", S["h3"]))
            for w in all_warnings:
                els.append(P(f"• {w}", S["warn"]))
            els.append(Spacer(1, 3*mm))

        # Assumptions — single concise block, no duplicates from resolver
        els.append(P("Calculation Assumptions", S["h3"]))
        assumptions = [
            "Layer order is inside-to-outside.",
            "Membranes (VCL, breather) are included in the build-up but excluded from thermal resistance unless specified.",
            "Ventilated cavities are excluded or treated conservatively.",
            "Timber fraction applied to framing zones (typically 15% default unless overridden per layer).",
            "Surface resistances applied in line with ISO 6946 methodology.",
            "U-values are preliminary profile checks only and require professional verification.",
        ]
        for a in assumptions:
            els.append(P(f"• {a}", S["body"]))

        els.append(Spacer(1, 4*mm))
        els.append(P(
            "Profile target check — these U-values are indicative calculations based on the parametric build-up configuration. "
            "Do not use for regulatory submission without independent verification.",
            S["note"]
        ))
        return els

    # ── Page 6: BOM / MTO ─────────────────────────────────────────────────────

    def _bom_page(self) -> list:
        S = self.S
        els = []
        els += self._section("Material Take-Off / BOM", "Quantities include waste factors")

        lines_by_type: dict[str, list] = {}
        for l in self.d.bom_lines:
            lines_by_type.setdefault(l["element_type"], []).append(l)

        for etype in ["ExternalWall", "Floor", "Roof"]:
            lines = lines_by_type.get(etype, [])
            if not lines:
                continue
            label = {"ExternalWall": "External Wall", "Floor": "Floor", "Roof": "Roof"}.get(etype, etype)
            els.append(P(label, S["h3"]))

            hdr = [
                P("Material", S["tbl_head"]), P("Role", S["tbl_head"]),
                P("Qty", S["tbl_head"]), P("Unit", S["tbl_head"]),
                P("Unit €", S["tbl_head"]), P("Line €", S["tbl_head"]),
                P("Ref", S["tbl_head"]),
            ]
            rows = [hdr]
            for l in sorted(lines, key=lambda x: x.get("position_order", 0)):
                ppu = fmtCost(l.get("price_per_unit")) if l.get("price_per_unit") else P("—", S["miss"])
                lc  = fmtCost(l.get("line_cost"))     if l.get("line_cost")     else P("Price missing — update register", S["miss"])
                rows.append([
                    P(l["material_name"], S["tbl_cell"]),
                    P(l.get("role",""), S["tbl_cell"]),
                    fmtN(l.get("order_quantity"), 2),
                    l.get("unit",""),
                    ppu,
                    lc,
                    P(l.get("supplier_ref","") or "—", S["tbl_mono"]),
                ])
            tbl = Table(rows, colWidths=[55*mm, 25*mm, 18*mm, 12*mm, 18*mm, 18*mm, CW-146*mm])
            tbl.setStyle(_tbl_style())
            els.append(tbl)
            els.append(Spacer(1, 3*mm))

        # Provisional sums section
        pa_lines = [l for l in self.d.bom_lines if l.get("role") == "opening"]
        if pa_lines or self.d.allowances:
            els.append(P("Provisional Allowances", S["h3"]))
            hdr = [P("Item", S["tbl_head"]), P("Qty", S["tbl_head"]),
                   P("Unit rate €", S["tbl_head"]), P("Total €", S["tbl_head"]), P("Notes", S["tbl_head"])]
            rows = [hdr]
            for l in pa_lines:
                rows.append([
                    P(l["material_name"], S["tbl_cell"]),
                    fmtN(l.get("order_quantity"), 0),
                    fmtCost(l.get("price_per_unit")),
                    fmtCost(l.get("line_cost")),
                    P(l.get("notes",""), S["note"]),
                ])
            tbl = Table(rows, colWidths=[65*mm, 15*mm, 25*mm, 25*mm, CW-130*mm])
            tbl.setStyle(_tbl_style())
            els.append(tbl)

        return els

    # ── Page 7: Material Evidence ──────────────────────────────────────────────

    def _evidence_page(self) -> list:
        S = self.S
        els = []
        els += self._section("Material Evidence Schedule", "Supplier links, datasheets and compliance evidence")

        visible = [m for m in self.d.materials if not (m.get("properties") or {}).get("hide_from_library")]

        hdr = [
            P("Material", S["tbl_head"]), P("Manufacturer", S["tbl_head"]),
            P("Spec ref", S["tbl_head"]), P("λ W/mK", S["tbl_head"]),
            P("Fire", S["tbl_head"]), P("Supplier", S["tbl_head"]),
            P("Datasheet", S["tbl_head"]), P("DOP", S["tbl_head"]),
            P("Evidence", S["tbl_head"]),
        ]
        rows = [hdr]

        link_style = ParagraphStyle("link", fontName="Helvetica", fontSize=7,
                                    textColor=C_BLUE, leading=9)

        def url_cell(url, short):
            if not url:
                return P("—", S["miss"])
            # ReportLab clickable hyperlink via <a href>
            safe = (url or "").replace("&", "&amp;").replace('"', "&quot;")
            return P(f'<a href="{safe}" color="#1d4ed8"><u>{short}</u></a>', link_style)

        status_style = {
            "verified": ParagraphStyle("ev_v", fontName="Helvetica-Bold", fontSize=7, textColor=C_GREEN, leading=9),
            "partial":  ParagraphStyle("ev_p", fontName="Helvetica-Bold", fontSize=7, textColor=C_AMBER, leading=9),
            "missing":  ParagraphStyle("ev_m", fontName="Helvetica-Bold", fontSize=7, textColor=C_RED,   leading=9),
        }

        for m in visible:
            lam_v = m.get("lambda_W_mK")
            lam = f"{lam_v:.3f}" if lam_v and lam_v > 0 else "—"
            ev = m.get("evidence_status", "missing")
            ev_label = {"verified": "✓ Verified", "partial": "~ Partial", "missing": "✗ Missing"}.get(ev, ev)
            rows.append([
                P(m["name"], S["tbl_cell"]),
                P(m.get("manufacturer") or "—", S["tbl_cell"]),
                P(m.get("spec_ref") or "—", S["tbl_mono"]),
                lam,
                P(m.get("fire_euroclass") or "—", S["tbl_cell"]),
                url_cell(m.get("supplier_url"), "Link"),
                url_cell(m.get("datasheet_url"), "PDF"),
                url_cell(m.get("dop_url"), "DOP"),
                P(ev_label, status_style.get(ev, S["tbl_cell"])),
            ])

        tbl = Table(rows, colWidths=[42*mm, 26*mm, 24*mm, 13*mm, 14*mm, 12*mm, 12*mm, 12*mm, CW-155*mm])
        tbl.setStyle(_tbl_style())
        els.append(tbl)
        return els

    # ── Page 8: Optional Packages ──────────────────────────────────────────────

    def _packages_page(self) -> list:
        S = self.S
        els = []
        els += self._section("Optional Packages / Provisional Sums", "Selected options only")

        pkg_lines = _active_pkg_lines(self.d.packages, self.d.pkg_overrides)

        if not pkg_lines:
            els.append(P("No optional packages selected.", S["note"]))
            return els

        hdr = [
            P("Package", S["tbl_head"]), P("Item", S["tbl_head"]),
            P("Qty", S["tbl_head"]), P("Low €", S["tbl_head"]),
            P("High €", S["tbl_head"]), P("Notes", S["tbl_head"]),
        ]
        rows = [hdr]
        total_low = total_high = 0
        for pl in pkg_lines:
            rows.append([
                P(pl["group_label"], S["tbl_cell"]),
                P(pl["name"], S["tbl_cell"]),
                str(pl["qty"]),
                fmtCost(pl.get("low")),
                fmtCost(pl.get("high")),
                "",
            ])
            total_low  += pl.get("low")  or 0
            total_high += pl.get("high") or 0

        rows.append([
            P("TOTAL", S["tbl_head"]), "",  "",
            P(fmtCost(total_low), S["tbl_head"]),
            P(fmtCost(total_high), S["tbl_head"]),
            "",
        ])

        tbl = Table(rows, colWidths=[32*mm, 55*mm, 12*mm, 20*mm, 20*mm, CW-139*mm])
        tbl.setStyle(_tbl_style())
        tbl.setStyle(TableStyle([
            ("FONTNAME",   (0, -1), (-1, -1), "Helvetica-Bold"),
            ("BACKGROUND", (0, -1), (-1, -1), BG_HEAD),
            ("LINEABOVE",  (0, -1), (-1, -1), 0.8, RULE2),
        ]))
        els.append(tbl)
        els.append(Spacer(1, 4*mm))

        notes = [
            "Furniture and sanitaryware are client discretion items unless specifically selected.",
            "Concrete and groundworks are separate extras unless selected.",
            "Optional package costs are provisional only and subject to supplier confirmation.",
        ]
        for n in notes:
            els.append(P(f"• {n}", S["note"]))
        return els

    # ── Page 9: Process / Timeline ────────────────────────────────────────────

    def _timeline_page(self) -> list:
        S = self.S
        els = []
        els += self._section("Process & Commercial Timeline", "From reservation to site delivery")

        steps = [
            ("1", "Reserve Online",                     "Secure your pod configuration with a reservation."),
            ("2", "10% Reservation Deposit",             "Reservation deposit confirms intent and locks configuration for review."),
            ("3", "Receive Review Pack",                 "Receive review drawings and permit-support documentation for local authority review."),
            ("4", "40% Contract Signing / Production Start", "Contract deposit triggers production scheduling. Build-up and specification confirmed at this stage."),
            ("5", "12–16 Weeks Production",              "Factory production period. Progress updates provided at key milestones."),
            ("6", "30% Payment Before Shipping",         "Third payment confirmed prior to transport preparation."),
            ("7", "Transport Confirmation",              "Shipping logistics confirmed. Site access, unloading, and crane requirements confirmed."),
            ("8", "20% Final Payment",                   "Final balance confirmed prior to shipment release."),
            ("9", "Shipment Release / Site Assembly",    "Delivery and site assembly. Commissioning and handover."),
        ]

        rows = [[P("#", S["tbl_head"]), P("Stage", S["tbl_head"]), P("Detail", S["tbl_head"])]]
        for num, stage, detail in steps:
            rows.append([
                P(num, ParagraphStyle("step_num", fontName="Helvetica-Bold", fontSize=9, textColor=INK, leading=11)),
                P(stage, ParagraphStyle("step", fontName="Helvetica-Bold", fontSize=8, textColor=INK, leading=10)),
                P(detail, S["body"]),
            ])

        tbl = Table(rows, colWidths=[10*mm, 55*mm, CW - 65*mm])
        tbl.setStyle(_tbl_style())
        # Alternating shading for steps
        for i in range(1, len(rows)):
            if i % 2 == 0:
                tbl.setStyle(TableStyle([("BACKGROUND", (0, i), (-1, i), BG_ALT)]))
        els.append(tbl)
        return els

    # ── Page 10: Disclaimers ──────────────────────────────────────────────────

    def _disclaimers_page(self) -> list:
        S = self.S
        els = []
        els += self._section("Disclaimers & Review Notes")

        disclaimers = [
            ("Parametric Configuration",
             "This pack is generated from a parametric pod configuration. All dimensions, build-up selections, "
             "and material specifications are subject to change as the design develops."),
            ("Preliminary Information Only",
             "This information is for preliminary review, budgeting, and coordination only. "
             "It is not suitable for tender issue, statutory application, or manufacture without independent verification."),
            ("Structural Design",
             "Structural design must be reviewed and approved by an appointed structural engineer. "
             "Foundation design, connection details, and load calculations are not included in this pack."),
            ("Building Regulation Compliance",
             "Local building regulation compliance must be reviewed by the appointed local professional, "
             "architect, or compliance consultant. Requirements vary by jurisdiction."),
            ("U-Values and Thermal Performance",
             "U-values are preliminary profile checks based on selected build-ups and stated assumptions. "
             "These are not final compliance calculations and require verification by a qualified energy assessor or building physicist."),
            ("Other Technical Disciplines",
             "Moisture, condensation risk (interstitial and surface), fire performance, acoustics, ventilation, "
             "electrical and plumbing compliance require separate professional review where applicable."),
            ("Dimensions and Openings",
             "Dimensions, opening positions, material selections and supplier information must be verified "
             "before manufacture. Plan drawings are generated parametrically and require architect review."),
            ("Prices and Costs",
             "Prices are provisional and subject to supplier confirmation, delivery charges, applicable taxes (VAT), "
             "labour, installation, site-specific conditions and project programme. Costs should be treated "
             "as indicative allowances only until confirmed quotations are received."),
            ("Issue Status",
             "This document is issued as: FOR REVIEW. It must not be used as a final design, construction, "
             "or compliance document without the issue status being updated following appropriate professional review."),
        ]

        for title, body in disclaimers:
            els.append(P(title, S["h3"]))
            els.append(P(body, S["disc"]))
            els.append(Spacer(1, 1*mm))

        els.append(Spacer(1, 6*mm))
        els.append(HRFlowable(width=CW, thickness=0.5, color=RULE2))
        els.append(Spacer(1, 2*mm))
        els.append(P(
            f"Generated by Top-R Solutions Pod Manufacture System · {self.d.generated_at.strftime('%d %b %Y')} · "
            f"Revision {self.d.revision} · {self.d.spec_name}",
            S["small"]
        ))
        return els

    # ── Assemble ───────────────────────────────────────────────────────────────

    def generate(self) -> bytes:
        doc = BaseDocTemplate(
            self.buf,
            pagesize=A4,
            leftMargin=ML, rightMargin=MR,
            topMargin=MT + 14, bottomMargin=MB + 12,
            title=f"{self.d.project_name} — Review Pack",
            author="Top-R Solutions",
        )
        frame = Frame(ML, MB + 12, CW, PH - MT - MB - 26, id="main")
        template = PageTemplate(id="main", frames=[frame], onPage=self._header_footer)
        doc.addPageTemplates([template])

        from reportlab.platypus import PageBreak
        story = []
        story += self._cover();             story.append(PageBreak())
        story += self._summary();           story.append(PageBreak())
        story += self._plan_page();         story.append(PageBreak())
        story += self._buildup_page();      story.append(PageBreak())
        story += self._thermal_page();      story.append(PageBreak())
        story += self._bom_page();          story.append(PageBreak())
        story += self._evidence_page();     story.append(PageBreak())
        story += self._packages_page();     story.append(PageBreak())
        story += self._timeline_page();     story.append(PageBreak())
        story += self._disclaimers_page()

        doc.build(story)
        return self.buf.getvalue()
