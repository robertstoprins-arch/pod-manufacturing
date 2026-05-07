"""
Client Quote PDF — POD CONFIGURATION & INDICATIVE QUOTE
Clean 8-page PDF for customer distribution. No internal costs, BOM quantities,
supplier refs, markup percentages or evidence schedules.
"""
from __future__ import annotations

import io
import math

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate, Frame, PageTemplate, Paragraph, Spacer,
    Table, TableStyle, HRFlowable, PageBreak, KeepTogether,
)
from reportlab.graphics import renderPDF

from app.skills.pdf_review_pack import (
    ReviewPackData,
    _plan_drawing,
    _active_pkg_lines,
    fmtCost,
    fmtN,
)

# ── Colours (client-friendly palette) ──────────────────────────────────────────
INK    = colors.HexColor("#1a1a1a")
INK2   = colors.HexColor("#444444")
MUTED  = colors.HexColor("#888888")
RULE   = colors.HexColor("#e0e0e0")
RULE2  = colors.HexColor("#cccccc")
BG_ALT = colors.HexColor("#f7f7f7")
BG_HEAD= colors.HexColor("#eeeeee")
ACCENT = colors.HexColor("#1a1a1a")
C_BLUE = colors.HexColor("#2563eb")
C_GREEN= colors.HexColor("#16a34a")
BG_GREEN=colors.HexColor("#f0fdf4")
BG_BLUE =colors.HexColor("#eff6ff")

PW, PH = A4
ML = MR = 18 * mm
MT = MB = 20 * mm
CW = PW - ML - MR


def _styles():
    def s(name, **kw):
        return ParagraphStyle(name, **kw)
    return {
        "h1":       s("h1",    fontName="Helvetica-Bold",  fontSize=22, textColor=INK,   leading=28, spaceAfter=4),
        "h2":       s("h2",    fontName="Helvetica-Bold",  fontSize=12, textColor=INK,   leading=15, spaceAfter=4, spaceBefore=12),
        "h3":       s("h3",    fontName="Helvetica-Bold",  fontSize=9,  textColor=INK,   leading=12, spaceAfter=3, spaceBefore=8),
        "body":     s("body",  fontName="Helvetica",       fontSize=8,  textColor=INK2,  leading=12, spaceAfter=2),
        "small":    s("small", fontName="Helvetica",       fontSize=7,  textColor=MUTED, leading=10),
        "note":     s("note",  fontName="Helvetica-Oblique",fontSize=7, textColor=MUTED, leading=10, spaceAfter=2),
        "tbl_head": s("tbl_head",fontName="Helvetica-Bold",fontSize=7,  textColor=INK2,  leading=9),
        "tbl_cell": s("tbl_cell",fontName="Helvetica",    fontSize=7,  textColor=INK2,  leading=9),
        "price_big":s("price_big",fontName="Helvetica-Bold",fontSize=22,textColor=INK,   leading=28),
        "price_lbl":s("price_lbl",fontName="Helvetica",   fontSize=8,  textColor=MUTED, leading=10),
        "cover_sub":s("cover_sub",fontName="Helvetica",   fontSize=10, textColor=INK2,  leading=14, spaceAfter=4),
        "disc":     s("disc",  fontName="Helvetica",       fontSize=7.5,textColor=INK2,  leading=12, spaceAfter=3),
        "bullet":   s("bullet",fontName="Helvetica",       fontSize=8,  textColor=INK2,  leading=13, spaceAfter=2, leftIndent=10, firstLineIndent=-6),
    }


def _tbl_style(has_header=True, row_alt=True):
    cmds = [
        ("FONTNAME",    (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE",    (0, 0), (-1, -1), 7),
        ("LEADING",     (0, 0), (-1, -1), 10),
        ("TOPPADDING",  (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING",(0,0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING",(0, 0), (-1, -1), 5),
        ("GRID",        (0, 0), (-1, -1), 0.3, RULE),
        ("VALIGN",      (0, 0), (-1, -1), "MIDDLE"),
    ]
    if has_header:
        cmds += [
            ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
            ("BACKGROUND", (0, 0), (-1, 0), BG_HEAD),
            ("LINEBELOW",  (0, 0), (-1, 0), 0.8, RULE2),
        ]
    if row_alt:
        cmds += [("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, BG_ALT])]
    return TableStyle(cmds)


def P(text, style):
    return Paragraph(str(text), style)


class ClientQuotePDF:
    def __init__(self, data: ReviewPackData, customer_name: str = ""):
        self.d = data
        self.S = _styles()
        self.buf = io.BytesIO()
        self._page_num = 0
        self.customer_name = customer_name or ""

    def _sp(self):
        """Compute selling price components from mid-range BOM + packages + finish catalogue."""
        d = self.d
        pkg_lines = _active_pkg_lines(d.packages, d.pkg_overrides)
        bom_total = d.bom_total or 0.0
        pkg_total = sum(
            ((pl["low"] or 0) + (pl["high"] or 0)) / 2
            for pl in pkg_lines
        )
        internal_mid = bom_total + pkg_total + (d.finish_total or 0.0)
        mp  = d.markup_percent
        vp  = d.vat_rate_percent
        rtn = d.round_to_nearest
        markup_amt = round(internal_mid * mp / 100, 2)
        ex_vat     = round(internal_mid + markup_amt, 2)
        vat_amt    = round(ex_vat * vp / 100, 2)
        inc_vat    = round(ex_vat + vat_amt, 2)
        rounded    = math.ceil(inc_vat / rtn) * rtn if rtn > 0 else inc_vat
        return {
            "internal_mid": internal_mid,
            "ex_vat":       ex_vat,
            "vat_amt":      vat_amt,
            "inc_vat":      inc_vat,
            "rounded":      rounded,
            "vat_pct":      vp,
        }

    def _header_footer(self, canvas, doc):
        canvas.saveState()
        self._page_num += 1
        pn = self._page_num
        canvas.setStrokeColor(RULE2)
        canvas.setLineWidth(0.5)
        canvas.line(ML, PH - MT + 8, PW - MR, PH - MT + 8)
        canvas.setFont("Helvetica", 6.5)
        canvas.setFillColor(MUTED)
        canvas.drawString(ML, PH - MT + 11, self.d.project_name.upper())
        canvas.drawRightString(PW - MR, PH - MT + 11, "POD CONFIGURATION & INDICATIVE QUOTE")
        canvas.line(ML, MB - 8, PW - MR, MB - 8)
        canvas.drawString(ML, MB - 15, f"Generated: {self.d.generated_at.strftime('%d %b %Y')}")
        canvas.drawString(ML + 80*mm, MB - 15, "INDICATIVE — SUBJECT TO FINAL REVIEW")
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
        sp = self._sp()
        w = float(geom.get("width_m", 0))
        l = float(geom.get("length_m", 0))
        h = float(geom.get("wall_height_m", 0))
        floor_m2 = w * l

        els = []
        els.append(Spacer(1, 12*mm))
        els.append(P("YOUR POD QUOTE", S["h1"]))
        els.append(P("POD CONFIGURATION &amp; INDICATIVE QUOTE", S["cover_sub"]))
        els.append(Spacer(1, 4*mm))
        els.append(HRFlowable(width=CW, thickness=1, color=RULE2, spaceAfter=6))

        # Pod name + customer
        info_rows = [[P("Pod name", S["tbl_head"]), d.spec_name or "—"]]
        if self.customer_name:
            info_rows.append([P("Prepared for", S["tbl_head"]), self.customer_name])
        info_rows += [
            [P("Date", S["tbl_head"]), d.generated_at.strftime("%d %b %Y")],
            [P("Floor area", S["tbl_head"]), f"{floor_m2:.1f} m²"],
            [P("External dimensions", S["tbl_head"]), f"{w:.2f} m × {l:.2f} m × {h:.2f} m (h)"],
            [P("Lead time", S["tbl_head"]), "12–16 weeks from confirmed order"],
        ]
        info_tbl = Table(info_rows, colWidths=[CW * 0.35, CW * 0.65])
        info_tbl.setStyle(_tbl_style(has_header=False, row_alt=False))
        els.append(info_tbl)
        els.append(Spacer(1, 8*mm))

        # Headline price box
        els.append(P("Indicative Selling Price", S["h3"]))
        price_data = [
            [P("Selling price ex VAT", S["price_lbl"]),
             P("VAT",                  S["price_lbl"]),
             P(f"Total incl VAT ({self.d.vat_rate_percent:.0f}%)", S["price_lbl"])],
            [P(fmtCost(sp["ex_vat"]),  S["price_big"]),
             P(f"+ {fmtCost(sp['vat_amt'])}", S["h3"]),
             P(fmtCost(sp["rounded"]), S["price_big"])],
        ]
        price_tbl = Table(price_data, colWidths=[CW * 0.38, CW * 0.22, CW * 0.40])
        price_tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), BG_ALT),
            ("TOPPADDING",    (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING",   (0, 0), (-1, -1), 8),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 8),
            ("GRID",          (0, 0), (-1, -1), 0.3, RULE2),
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ]))
        els.append(price_tbl)
        els.append(Spacer(1, 4*mm))
        els.append(P(
            "Configured pod proposal · Indicative quote for review · "
            "Lead time: 12–16 weeks from confirmed order",
            S["note"]
        ))
        els.append(Spacer(1, 6*mm))
        els.append(P(
            "This quote is indicative and subject to final specification, site survey, "
            "delivery, installation and professional review.",
            S["note"]
        ))
        return els

    # ── Shared helper: Drawing → Flowable ────────────────────────────────────

    @staticmethod
    def _drawing_flowable(drawing):
        from reportlab.platypus import Flowable as _Flowable
        class _DF(_Flowable):
            def __init__(self, d):
                super().__init__()
                self._d = d
                self.width  = d.width
                self.height = d.height
            def draw(self):
                renderPDF.draw(self._d, self.canv, 0, 0)
        return _DF(drawing)

    # ── Page 2: Architectural Plan & Opening Schedule ─────────────────────────

    def _design_summary(self) -> list:
        S = self.S
        d = self.d
        geom = d.geometry
        els = []
        els += self._section("Architectural Plan",
                             "Configurator floor plan — dimensions indicative, for review only")

        wall_thick_mm = float((d.wall_bu or {}).get("total_thickness_mm", 300))
        # Give generous height so offset dim lines outside the pod boundary are visible
        plan_h = 160 * mm
        drawing, opening_labels = _plan_drawing(
            geom=geom,
            wall_thick_mm=wall_thick_mm,
            draw_w=CW,
            draw_h=plan_h,
            pod_name=d.spec_name or "",
        )
        els.append(self._drawing_flowable(drawing))
        els.append(Spacer(1, 3*mm))
        els.append(P(
            "Plan generated from parametric configuration. Offset dimensions shown where set. "
            "Door swing directions and opening positions require verification before permit.",
            S["note"]
        ))

        # Opening schedule — ref, type, size (w×h mm), wall, offset from corner
        if opening_labels:
            els.append(Spacer(1, 3*mm))
            els.append(P("Opening Schedule", S["h3"]))

            # Rebuild with offset info from geometry
            openings = geom.get("openings", [])
            rl_list  = [ro for ro in (geom.get("roof_openings") or []) if ro.get("selected")]

            sched_rows = [[
                P("Ref",        S["tbl_head"]),
                P("Type",       S["tbl_head"]),
                P("Width mm",   S["tbl_head"]),
                P("Height mm",  S["tbl_head"]),
                P("Wall",       S["tbl_head"]),
                P("Offset from corner mm", S["tbl_head"]),
            ]]
            door_c = win_c = french_c = rl_c = 0
            for o in openings:
                ot = o.get("type", "window")
                if ot == "door":
                    door_c += 1; ref = f"D{door_c}"
                elif ot == "french_door":
                    french_c += 1; ref = f"FD{french_c}"
                else:
                    win_c += 1; ref = f"W{win_c}"
                w_mm  = int(float(o.get("width_m",  1.0)) * 1000)
                h_mm  = int(float(o.get("height_m", 1.0)) * 1000)
                wall  = o.get("wall", "—")
                xoff  = o.get("x_offset_m")
                offset_str = f"{int(float(xoff)*1000)}" if xoff not in (None, "") else "centred"
                sched_rows.append([ref, ot.replace("_", " ").title(), str(w_mm), str(h_mm), wall, offset_str])

            for ro in rl_list:
                rl_c += 1; ref = f"RL{rl_c}"
                rw = int(float(ro.get("width_mm",  600)))
                rh = int(float(ro.get("height_mm", 900)))
                rx = ro.get("x_offset_mm")
                ry = ro.get("y_offset_mm")
                if rx not in (None, "") and ry not in (None, ""):
                    off_str = f"x={int(float(rx))} y={int(float(ry))}"
                else:
                    off_str = "centred"
                sched_rows.append([ref, "Rooflight / Skylight", str(rw), str(rh), "Roof", off_str])

            col_w = [CW*0.09, CW*0.20, CW*0.12, CW*0.12, CW*0.10, CW*0.37]
            sched_tbl = Table(sched_rows, colWidths=col_w)
            sched_tbl.setStyle(_tbl_style())
            els.append(sched_tbl)

        # Pod dimensions summary below schedule
        w = float(geom.get("width_m", 0))
        l = float(geom.get("length_m", 0))
        h = float(geom.get("wall_height_m", 0))
        els.append(Spacer(1, 3*mm))
        els.append(P("Pod Dimensions", S["h3"]))
        dims_rows = [
            ["External width",   f"{w:.2f} m"],
            ["External length",  f"{l:.2f} m"],
            ["Wall height",      f"{h:.2f} m"],
            ["Floor area",       f"{w * l:.1f} m²"],
            ["Wall build-up",    f"{int(wall_thick_mm)} mm"],
        ]
        dim_tbl = Table(dims_rows, colWidths=[CW * 0.45, CW * 0.55])
        dim_tbl.setStyle(_tbl_style(has_header=False))
        els.append(dim_tbl)

        # Selected options
        pkg_lines = _active_pkg_lines(d.packages, d.pkg_overrides)
        if pkg_lines:
            els.append(Spacer(1, 3*mm))
            els.append(P("Selected Options", S["h3"]))
            opt_rows = [[P("Option", S["tbl_head"]), P("Status", S["tbl_head"])]]
            for pl in pkg_lines:
                opt_rows.append([pl["name"], P("✓ Selected", S["tbl_cell"])])
            opt_tbl = Table(opt_rows, colWidths=[CW * 0.75, CW * 0.25])
            opt_tbl.setStyle(_tbl_style())
            els.append(opt_tbl)

        return els

    # ── Page 3: Comfort & Performance ─────────────────────────────────────────

    def _performance(self) -> list:
        S = self.S
        d = self.d
        els = []
        els += self._section("Comfort & Performance",
                             "Designed for year-round comfort — subject to final professional review")
        els.append(P(
            "Designed as an insulated timber pod system for year-round comfort. "
            "Thermal performance figures are calculated from the selected build-up specification "
            "and are subject to final professional review.",
            S["body"]
        ))
        els.append(Spacer(1, 4*mm))

        rows = [[P("Element", S["tbl_head"]), P("U-value W/m²K", S["tbl_head"]),
                 P("Thickness mm", S["tbl_head"]), P("Performance", S["tbl_head"])]]
        for bu, label in [(d.wall_bu, "External Wall"), (d.floor_bu, "Floor"), (d.roof_bu, "Roof")]:
            if bu:
                t = bu.get("targets", [{}])[0] if bu.get("targets") else {}
                perf = "Good" if t.get("passes") else "Review"
                rows.append([label, f"{bu['u_value']:.3f}", f"{bu['total_thickness_mm']:.0f}", perf])
            else:
                rows.append([label, "—", "—", "—"])
        tbl = Table(rows, colWidths=[CW*0.3, CW*0.2, CW*0.25, CW*0.25])
        tbl.setStyle(_tbl_style())
        els.append(tbl)
        els.append(Spacer(1, 6*mm))
        els.append(P("Key features", S["h3"]))
        bullets = [
            "Insulated timber frame construction",
            "Vapour control layer (VCL) included",
            "Breather membrane included",
            "Service void for electrical/plumbing routes",
            "Roof designed for green roof or EPDM finish",
            "All U-values calculated to ISO 6946 / ISO 10211 methodology",
        ]
        for b in bullets:
            els.append(P(f"• {b}", S["bullet"]))
        return els

    # ── Page 3b: Selected Finishes & Options ─────────────────────────────────

    def _finishes(self) -> list:
        S = self.S
        d = self.d
        lines = [l for l in (d.finish_lines or []) if l.get("included", True)]
        if not lines:
            return []

        CUSTOMER_SAFE = {"approved_for_customer_pdf", "own_photo",
                         "licensed_stock", "generated_placeholder"}

        # Group by cost_group, preserving insertion order
        GROUP_ORDER = [
            "Finishes", "Sanitaryware", "Furniture / Client Discretion",
            "Kitchenette", "Lighting", "CCTV / Data", "Solar / Battery",
            "Heating + Ventilation", "Delivery / Install", "Other",
        ]
        groups: dict[str, list] = {}
        for l in lines:
            g = l.get("cost_group", "Other")
            groups.setdefault(g, [])
            # Deduplicate by item_id within group (packages may duplicate manual items)
            if not any(x["item_id"] == l["item_id"] for x in groups[g]):
                groups[g].append(l)

        els = []
        els += self._section(
            "Selected Finishes & Options",
            "Your selected finish and furniture specifications"
        )

        for group_name in GROUP_ORDER + [k for k in groups if k not in GROUP_ORDER]:
            items = groups.get(group_name)
            if not items:
                continue

            els.append(P(group_name, S["h3"]))

            rows = [[
                P("Item",        S["tbl_head"]),
                P("Description", S["tbl_head"]),
                P("Source",      S["tbl_head"]),
                P("Price",       S["tbl_head"]),
            ]]

            for l in items:
                name      = l.get("name") or l.get("code", "—")
                desc      = l.get("customer_description") or ""
                source    = l.get("package_name") or "Selected option"
                cost      = l.get("line_cost")
                price_txt = fmtCost(cost) if cost else "Included / POA"
                spec_url  = l.get("specification_url")  # only present if admin marked public

                # Item name cell — append spec link if public
                if spec_url:
                    name_cell = P(f'{name}<br/><font size="6" color="#2563eb">{spec_url[:60]}</font>', S["tbl_cell"])
                else:
                    name_cell = P(name, S["tbl_cell"])

                rows.append([
                    name_cell,
                    P(desc[:120] if desc else "—", S["tbl_cell"]),
                    P(source, S["tbl_cell"]),
                    P(price_txt, S["tbl_cell"]),
                ])

            tbl = Table(rows, colWidths=[CW * 0.28, CW * 0.30, CW * 0.25, CW * 0.17])
            tbl.setStyle(_tbl_style())
            els.append(tbl)
            els.append(Spacer(1, 3*mm))

        els.append(P(
            "Finish and furniture options are indicative selections. Final specifications, "
            "colours and models are subject to confirmation and availability at time of order.",
            S["note"]
        ))
        return els

    # ── Page 4: Price Breakdown ────────────────────────────────────────────────

    def _price_breakdown(self) -> list:
        S = self.S
        d = self.d
        sp = self._sp()
        els = []
        els += self._section("Price Breakdown",
                             "Package-level selling prices — all prices indicative and subject to final review")

        # Envelope / shell total from BOM (selling price, not internal cost)
        bom_total    = d.bom_total or 0.0
        mp           = d.markup_percent
        vp           = d.vat_rate_percent
        rtn          = d.round_to_nearest

        def _selling(cost):
            ex = round(cost * (1 + mp / 100), 2)
            vat = round(ex * vp / 100, 2)
            return ex, vat

        shell_ex, shell_vat = _selling(bom_total)

        price_rows = [[
            P("Item", S["tbl_head"]),
            P("Selling price ex VAT €", S["tbl_head"]),
        ]]

        total_ex = 0.0

        if bom_total > 0:
            price_rows.append(["Pod envelope / shell (materials)", fmtCost(shell_ex)])
            total_ex += shell_ex

        pkg_lines = _active_pkg_lines(d.packages, d.pkg_overrides)
        for pl in pkg_lines:
            mid = ((pl["low"] or 0) + (pl["high"] or 0)) / 2
            ex, _ = _selling(mid)
            price_rows.append([pl["name"], fmtCost(ex)])
            total_ex += ex

        # Finish catalogue lines — group into cost groups, show selling price
        finish_lines = [l for l in (d.finish_lines or []) if l.get("included", True) and l.get("line_cost")]
        if finish_lines:
            # Deduplicate by item_id
            seen = set()
            unique = []
            for l in finish_lines:
                if l["item_id"] not in seen:
                    seen.add(l["item_id"])
                    unique.append(l)
            finish_internal = sum(l["line_cost"] for l in unique)
            finish_ex, _ = _selling(finish_internal)
            price_rows.append(["Finishes & furniture options", fmtCost(finish_ex)])
            total_ex += finish_ex

        # Summary rows
        vat_total = round(total_ex * vp / 100, 2)
        inc_total = round(total_ex + vat_total, 2)
        rounded   = math.ceil(inc_total / rtn) * rtn if rtn > 0 else inc_total

        price_rows.append([P(f"Subtotal ex VAT", S["tbl_head"]), P(fmtCost(total_ex), S["tbl_head"])])
        price_rows.append([P(f"VAT ({vp:.0f}%)",              S["tbl_head"]), P(fmtCost(vat_total), S["tbl_head"])])
        price_rows.append([P("Total incl VAT",                S["tbl_head"]), P(fmtCost(rounded),   S["tbl_head"])])

        tbl = Table(price_rows, colWidths=[CW * 0.65, CW * 0.35])
        tbl.setStyle(_tbl_style())
        n = len(price_rows)
        tbl.setStyle(TableStyle([
            ("FONTNAME",   (0, n-3), (-1, -1), "Helvetica-Bold"),
            ("BACKGROUND", (0, n-3), (-1, -1), BG_GREEN),
            ("LINEABOVE",  (0, n-3), (-1, n-3), 0.8, RULE2),
        ]))
        els.append(tbl)
        els.append(Spacer(1, 4*mm))
        els.append(P(
            "All prices are indicative provisional selling prices only. Final price depends on "
            "confirmed specification, site conditions, delivery and installation.",
            S["note"]
        ))
        return els

    # ── Page 5: Options / Upgrades ────────────────────────────────────────────

    def _upgrades(self) -> list:
        S = self.S
        els = []
        els += self._section("Options & Upgrades", "Available upgrades — tick to add to your configuration")

        upgrades = [
            ("PV-Ready Roof Provision",    "Spare conduit and marked fixing zones. PV not included."),
            ("Solar PV Panels",            "Provisional option only. Final design by specialist."),
            ("Battery Storage",            "Provisional option only. Final design by specialist."),
            ("Smart Electric Heating",     "WiFi-controlled smart radiators upgrade."),
            ("Air-to-Air Heat Pump",       "Heating and cooling upgrade. Installation by qualified installer."),
            ("MVHR Premium Ventilation",   "Mechanical heat recovery ventilation — premium option."),
            ("CCTV / Data Prewire",        "CAT6 home-runs and camera position prewire allowance."),
            ("Interior Finishes Package",  "Flooring, paint, trims and internal finish allowance."),
            ("Kitchenette Allowance",      "Client discretion. Final specification subject to selection."),
            ("Furniture Package",          "Client discretion allowance. Brand to be confirmed."),
        ]
        rows = [[P("Upgrade", S["tbl_head"]), P("Notes", S["tbl_head"])]]
        for name, notes in upgrades:
            rows.append([name, P(notes, S["tbl_cell"])])
        tbl = Table(rows, colWidths=[CW * 0.35, CW * 0.65])
        tbl.setStyle(_tbl_style())
        els.append(tbl)
        els.append(Spacer(1, 4*mm))
        els.append(P(
            "Solar PV and battery storage are provisional options only. Final design, structural "
            "fixing, electrical design, grid connection and certification must be confirmed by "
            "appointed specialists.",
            S["note"]
        ))
        return els

    # ── Page 6: Lead Time & Payment Plan ──────────────────────────────────────

    def _payment_plan(self) -> list:
        S = self.S
        sp = self._sp()
        total = sp["rounded"]
        els = []
        els += self._section("Lead Time & Payment Plan")

        steps = [
            ("Reserve online",                 "10% reservation deposit",             round(total * 0.10)),
            ("Review pack / permit support",   "Information pack issued",              None),
            ("Contract signing / production",  "40% — production start",              round(total * 0.40)),
            ("12–16 weeks production",         "Manufacturing period",                 None),
            ("Before shipping",                "30% — prior to dispatch",             round(total * 0.30)),
            ("Transport confirmation",         "Delivery scheduling confirmed",        None),
            ("Final payment",                  "20% on delivery",                     round(total * 0.20)),
            ("Delivery / site assembly",       "Delivery and handover",                None),
        ]
        rows = [[P("Stage", S["tbl_head"]), P("Description", S["tbl_head"]), P("Amount incl VAT €", S["tbl_head"])]]
        for stage, desc, amt in steps:
            rows.append([stage, desc, fmtCost(amt) if amt else "—"])
        tbl = Table(rows, colWidths=[CW * 0.30, CW * 0.45, CW * 0.25])
        tbl.setStyle(_tbl_style())
        els.append(tbl)
        els.append(Spacer(1, 4*mm))
        els.append(P(f"Total indicative price incl VAT: {fmtCost(total)}", S["h3"]))
        return els

    # ── Page 7: Delivery Notes ────────────────────────────────────────────────

    def _delivery(self) -> list:
        S = self.S
        els = []
        els += self._section("Delivery & Client Notes")
        els.append(P(
            "Delivery is provisional and subject to final address, site access, road restrictions, "
            "unloading method, crane/forklift requirements and site readiness.",
            S["body"]
        ))
        els.append(Spacer(1, 3*mm))
        rows = [
            [P("Item", S["tbl_head"]),    P("Detail", S["tbl_head"])],
            ["Delivery allowance",        "Provisional"],
            ["Final delivery cost",       "Subject to confirmation after site survey"],
            ["Crane / lifting",           "Subject to site access and unloading method"],
            ["Road restrictions",         "Subject to local authority requirements"],
            ["Site readiness",            "Foundation / groundworks must be complete at delivery"],
        ]
        tbl = Table(rows[1:], colWidths=[CW * 0.4, CW * 0.6])
        tbl.setStyle(_tbl_style(has_header=False))
        els.append(tbl)
        els.append(Spacer(1, 6*mm))
        els.append(P("What to expect", S["h3"]))
        info = [
            "We will confirm exact delivery logistics after order confirmation.",
            "A site survey may be required prior to delivery scheduling.",
            "Site must have clear access for transport and lifting equipment.",
            "Groundworks and foundation must be complete and ready to receive the pod.",
            "All MEP connections (electrical, plumbing, heating) are excluded unless specifically included in the selected packages.",
        ]
        for item in info:
            els.append(P(f"• {item}", S["bullet"]))
        return els

    # ── Page 8: Disclaimer ────────────────────────────────────────────────────

    def _disclaimer(self) -> list:
        S = self.S
        els = []
        els += self._section("Terms & Disclaimer")
        paras = [
            "This offer is indicative and subject to final specification, site conditions, "
            "delivery, installation, VAT/taxes and professional review where required.",
            "Groundworks, foundations, service connections, planning/statutory submissions "
            "and local approvals are excluded unless specifically stated.",
            "Solar PV, battery systems, heating, ventilation, electrical and plumbing items "
            "require final specialist review and installation by competent/qualified installers "
            "where required.",
            "Images, drawings and dimensions are generated from the selected configuration "
            "and must be verified before manufacture.",
            "Prices shown are indicative selling prices inclusive of VAT at the current rate. "
            "Final invoice price will be confirmed at contract stage.",
            "Lead times are indicative from confirmed order and production slot allocation. "
            "Exact scheduling is confirmed at contract stage.",
        ]
        for para in paras:
            els.append(P(para, S["disc"]))
            els.append(Spacer(1, 2*mm))
        return els

    # ── Assemble ───────────────────────────────────────────────────────────────

    def generate(self) -> bytes:
        doc = BaseDocTemplate(
            self.buf, pagesize=A4,
            leftMargin=ML, rightMargin=MR, topMargin=MT + 12, bottomMargin=MB + 12,
        )
        frame = Frame(ML, MB + 10, CW, PH - MT - MB - 22, id="main")
        template = PageTemplate(id="page", frames=[frame],
                                onPage=self._header_footer)
        doc.addPageTemplates([template])

        story = []
        story += self._cover();            story.append(PageBreak())
        story += self._design_summary();   story.append(PageBreak())
        story += self._performance();      story.append(PageBreak())
        finishes = self._finishes()
        if finishes:
            story += finishes;             story.append(PageBreak())
        story += self._price_breakdown();  story.append(PageBreak())
        story += self._upgrades();         story.append(PageBreak())
        story += self._payment_plan();     story.append(PageBreak())
        story += self._delivery();         story.append(PageBreak())
        story += self._disclaimer()

        doc.build(story)
        return self.buf.getvalue()
