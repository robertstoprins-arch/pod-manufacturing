"""
Deposit Invoice PDF generator.

Produces a clean A4 PDF invoice for the deposit amount on an accepted quote.
No internal costs, markup percentages, BOM quantities or supplier data.
"""
from __future__ import annotations

import io
from datetime import date

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate, Frame, PageTemplate,
    Paragraph, Spacer, Table, TableStyle, HRFlowable, KeepTogether,
)

INK   = colors.HexColor("#1a1a1a")
INK2  = colors.HexColor("#444444")
MUTED = colors.HexColor("#888888")
RULE  = colors.HexColor("#e0e0e0")
BG    = colors.HexColor("#f7f7f7")
NAVY  = colors.HexColor("#1e3a5f")
GREEN = colors.HexColor("#16a34a")

PW, PH = A4
ML = MR = 18 * mm
MT = MB = 20 * mm
CW = PW - ML - MR


def _styles():
    def s(name, **kw):
        return ParagraphStyle(name, **kw)
    return {
        "co_name":   s("co_name",  fontName="Helvetica-Bold", fontSize=16, textColor=NAVY,  leading=20),
        "co_detail": s("co_detail",fontName="Helvetica",      fontSize=8,  textColor=INK2,  leading=12),
        "doc_title": s("doc_title",fontName="Helvetica-Bold", fontSize=22, textColor=INK,   leading=26, spaceAfter=2),
        "doc_sub":   s("doc_sub",  fontName="Helvetica",      fontSize=9,  textColor=MUTED, leading=12),
        "section":   s("section",  fontName="Helvetica-Bold", fontSize=8,  textColor=MUTED, leading=11, spaceBefore=14, spaceAfter=4),
        "body":      s("body",     fontName="Helvetica",      fontSize=9,  textColor=INK2,  leading=13),
        "bold":      s("bold",     fontName="Helvetica-Bold", fontSize=9,  textColor=INK,   leading=13),
        "small":     s("small",    fontName="Helvetica",      fontSize=7.5,textColor=MUTED, leading=11),
        "tbl_hdr":   s("tbl_hdr", fontName="Helvetica-Bold", fontSize=8,  textColor=INK2,  leading=10),
        "tbl_cell":  s("tbl_cell",fontName="Helvetica",      fontSize=8,  textColor=INK2,  leading=10),
        "amount_big":s("amount_big",fontName="Helvetica-Bold",fontSize=20,textColor=GREEN,  leading=24),
        "amount_lbl":s("amount_lbl",fontName="Helvetica",    fontSize=8,  textColor=MUTED,  leading=11),
        "note":      s("note",     fontName="Helvetica-Oblique",fontSize=8,textColor=MUTED, leading=12, spaceAfter=3),
    }


def _tbl(cmds):
    base = [
        ("FONTNAME",    (0,0),(-1,-1),"Helvetica"),
        ("FONTSIZE",    (0,0),(-1,-1), 8),
        ("LEADING",     (0,0),(-1,-1), 11),
        ("TOPPADDING",  (0,0),(-1,-1), 4),
        ("BOTTOMPADDING",(0,0),(-1,-1), 4),
        ("LEFTPADDING", (0,0),(-1,-1), 6),
        ("RIGHTPADDING",(0,0),(-1,-1), 6),
        ("VALIGN",      (0,0),(-1,-1),"MIDDLE"),
    ]
    return TableStyle(base + cmds)


def build_deposit_invoice(quote: dict, settings: dict) -> bytes:
    """
    quote:    dict with keys matching QuoteOut fields
    settings: dict with keys matching SettingsOut fields
    Returns:  raw PDF bytes
    """
    buf = io.BytesIO()
    doc = BaseDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=ML, rightMargin=MR,
        topMargin=MT, bottomMargin=MB,
        title="Deposit Invoice",
    )
    frame = Frame(ML, MB, CW, PH - MT - MB, id="main")
    doc.addPageTemplates([PageTemplate(id="page", frames=[frame])])

    ST = _styles()
    cur = quote.get("currency", "EUR")
    vat_rate = settings.get("vat_rate_percent", 21.0)

    # ── Invoice reference
    qnum = quote.get("quote_number") or str(quote.get("id", ""))[:8]
    inv_ref = f"INV-{qnum}-DEP"
    today = date.today().strftime("%-d %B %Y") if hasattr(date.today(), "strftime") else date.today().isoformat()
    try:
        today = date.today().strftime("%d %B %Y")
    except Exception:
        today = date.today().isoformat()

    due_days = settings.get("payment_terms_days") or 7
    due_date_obj = date.today()
    try:
        from datetime import timedelta
        due_date_obj = date.today() + timedelta(days=due_days)
        due_date = due_date_obj.strftime("%d %B %Y")
    except Exception:
        due_date = f"{due_days} days from issue"

    co_name = settings.get("company_name") or "Pod Manufacturer"
    co_addr = (settings.get("company_address") or "").replace("\n", "<br/>")
    co_email = settings.get("company_email") or ""
    co_phone = settings.get("company_phone") or ""
    vat_num = settings.get("vat_number") or ""

    client_name = quote.get("client_name") or "Client"
    quote_title = quote.get("title", "")

    total_ex = quote.get("total_ex_vat")
    total_inc = quote.get("total_inc_vat")
    dep_pct = quote.get("deposit_percent")
    dep_amt = quote.get("deposit_amount")

    # Derive deposit amount if not stored
    if dep_amt is None and dep_pct and total_ex:
        dep_amt = round(float(total_ex) * float(dep_pct) / 100, 2)

    # Derive VAT on deposit
    dep_ex_vat = None
    dep_vat = None
    dep_inc_vat = dep_amt
    if dep_amt is not None and vat_rate:
        dep_ex_vat = round(float(dep_amt) / (1 + vat_rate / 100), 2)
        dep_vat = round(float(dep_amt) - dep_ex_vat, 2)
        dep_inc_vat = float(dep_amt)

    def fmt(v):
        if v is None:
            return "—"
        return f"{cur} {v:,.2f}"

    elems = []

    # ── Header: company left, invoice details right ──────────────────────────
    co_lines = [Paragraph(co_name, ST["co_name"])]
    if co_addr:
        co_lines.append(Paragraph(co_addr, ST["co_detail"]))
    if co_email:
        co_lines.append(Paragraph(co_email, ST["co_detail"]))
    if co_phone:
        co_lines.append(Paragraph(co_phone, ST["co_detail"]))
    if vat_num:
        co_lines.append(Paragraph(f"VAT Reg: {vat_num}", ST["co_detail"]))

    inv_lines = [
        Paragraph("DEPOSIT INVOICE", ST["doc_title"]),
        Paragraph(inv_ref, ST["doc_sub"]),
        Spacer(1, 4),
        Paragraph(f"<b>Issue date:</b> {today}", ST["body"]),
        Paragraph(f"<b>Payment due:</b> {due_date}", ST["body"]),
    ]

    hdr_tbl = Table(
        [[co_lines, inv_lines]],
        colWidths=[CW * 0.5, CW * 0.5],
    )
    hdr_tbl.setStyle(_tbl([
        ("VALIGN",      (0,0),(-1,-1),"TOP"),
        ("LEFTPADDING", (0,0),(-1,-1), 0),
        ("RIGHTPADDING",(0,0),(-1,-1), 0),
        ("TOPPADDING",  (0,0),(-1,-1), 0),
        ("BOTTOMPADDING",(0,0),(-1,-1), 0),
        ("ALIGN",       (1,0),(1,0),   "RIGHT"),
    ]))
    elems.append(hdr_tbl)
    elems.append(Spacer(1, 6*mm))
    elems.append(HRFlowable(width=CW, thickness=1.5, color=NAVY))
    elems.append(Spacer(1, 5*mm))

    # ── Bill to ──────────────────────────────────────────────────────────────
    elems.append(Paragraph("BILL TO", ST["section"]))
    elems.append(Paragraph(f"<b>{client_name}</b>", ST["bold"]))

    # ── Quote reference ──────────────────────────────────────────────────────
    elems.append(Spacer(1, 4*mm))
    elems.append(Paragraph("DESCRIPTION", ST["section"]))

    desc_rows = [
        [Paragraph("Description", ST["tbl_hdr"]),
         Paragraph("Quote Ref", ST["tbl_hdr"]),
         Paragraph("Amount", ST["tbl_hdr"])],
        [Paragraph(f"Deposit payment — {quote_title}", ST["tbl_cell"]),
         Paragraph(quote.get("quote_number") or "—", ST["tbl_cell"]),
         Paragraph(fmt(dep_inc_vat), ST["tbl_cell"])],
    ]
    desc_tbl = Table(desc_rows, colWidths=[CW * 0.55, CW * 0.20, CW * 0.25])
    desc_tbl.setStyle(_tbl([
        ("BACKGROUND",  (0,0),(-1,0), BG),
        ("FONTNAME",    (0,0),(-1,0),"Helvetica-Bold"),
        ("LINEBELOW",   (0,0),(-1,0), 0.5, RULE),
        ("ALIGN",       (2,0),(2,-1),"RIGHT"),
        ("GRID",        (0,0),(-1,-1), 0.3, RULE),
    ]))
    elems.append(desc_tbl)

    # ── Price breakdown ───────────────────────────────────────────────────────
    elems.append(Spacer(1, 4*mm))
    price_rows = []
    if dep_ex_vat is not None:
        price_rows.append(["Deposit ex. VAT", fmt(dep_ex_vat)])
        price_rows.append([f"VAT ({vat_rate:.0f}%)", fmt(dep_vat)])

    dep_pct_str = f" ({float(dep_pct):.0f}% of total)" if dep_pct else ""
    price_rows.append([f"Deposit due{dep_pct_str}", fmt(dep_inc_vat)])

    price_data = [[Paragraph(r[0], ST["tbl_cell"]),
                   Paragraph(r[1], ST["tbl_cell"])] for r in price_rows]

    price_tbl = Table(price_data, colWidths=[CW * 0.75, CW * 0.25])
    price_tbl.setStyle(_tbl([
        ("ALIGN",       (1,0),(1,-1),"RIGHT"),
        ("LINEABOVE",   (0,-1),(-1,-1), 1.5, NAVY),
        ("FONTNAME",    (0,-1),(-1,-1),"Helvetica-Bold"),
        ("FONTSIZE",    (0,-1),(-1,-1), 10),
        ("TEXTCOLOR",   (0,-1),(-1,-1), GREEN),
        ("BACKGROUND",  (0,-1),(-1,-1), colors.HexColor("#f0fdf4")),
        ("TOPPADDING",  (0,-1),(-1,-1), 6),
        ("BOTTOMPADDING",(0,-1),(-1,-1), 6),
    ]))

    # Right-align price table
    price_wrap = Table([[None, price_tbl]], colWidths=[CW * 0.35, CW * 0.65])
    price_wrap.setStyle(_tbl([
        ("LEFTPADDING", (0,0),(-1,-1), 0),
        ("RIGHTPADDING",(0,0),(-1,-1), 0),
        ("TOPPADDING",  (0,0),(-1,-1), 0),
        ("BOTTOMPADDING",(0,0),(-1,-1), 0),
    ]))
    elems.append(price_wrap)

    # ── Payment instructions ──────────────────────────────────────────────────
    bank_name   = settings.get("bank_name")
    bank_acc    = settings.get("bank_account_name")
    bank_iban   = settings.get("bank_iban")
    bank_bic    = settings.get("bank_bic")

    if any([bank_name, bank_iban, bank_bic]):
        elems.append(Spacer(1, 6*mm))
        elems.append(HRFlowable(width=CW, thickness=0.5, color=RULE))
        elems.append(Paragraph("PAYMENT INSTRUCTIONS", ST["section"]))

        bank_rows = []
        if bank_acc:    bank_rows.append(["Account name:", bank_acc])
        if bank_name:   bank_rows.append(["Bank:", bank_name])
        if bank_iban:   bank_rows.append(["IBAN:", bank_iban])
        if bank_bic:    bank_rows.append(["BIC / SWIFT:", bank_bic])
        bank_rows.append(["Reference:", inv_ref])

        bank_data = [[Paragraph(r[0], ST["bold"]),
                      Paragraph(r[1], ST["body"])] for r in bank_rows]
        bank_tbl = Table(bank_data, colWidths=[CW * 0.25, CW * 0.75])
        bank_tbl.setStyle(_tbl([
            ("BACKGROUND",  (0,0),(-1,-1), BG),
            ("GRID",        (0,0),(-1,-1), 0.3, RULE),
        ]))
        elems.append(bank_tbl)
        elems.append(Spacer(1, 3*mm))
        elems.append(Paragraph(
            f"Please use <b>{inv_ref}</b> as the payment reference. "
            f"Payment is due within <b>{due_days} days</b> of this invoice.",
            ST["note"]
        ))

    # ── Notes / spec summary ─────────────────────────────────────────────────
    spec = quote.get("spec_summary") or {}
    spec_parts = []
    if spec.get("width_m") and spec.get("length_m"):
        spec_parts.append(f"{spec['width_m']}m × {spec['length_m']}m")
    if spec.get("floor_area_m2"):
        spec_parts.append(f"{spec['floor_area_m2']}m² floor area")
    if spec.get("roof_type"):
        spec_parts.append(spec["roof_type"])

    if spec_parts:
        elems.append(Spacer(1, 4*mm))
        elems.append(Paragraph("POD SPECIFICATION", ST["section"]))
        elems.append(Paragraph(" · ".join(spec_parts), ST["body"]))

    if quote.get("notes"):
        elems.append(Spacer(1, 4*mm))
        elems.append(Paragraph("NOTES", ST["section"]))
        elems.append(Paragraph(quote["notes"], ST["note"]))

    # ── Footer note ──────────────────────────────────────────────────────────
    elems.append(Spacer(1, 8*mm))
    elems.append(HRFlowable(width=CW, thickness=0.5, color=RULE))
    elems.append(Spacer(1, 3*mm))
    footer_parts = [co_name]
    if vat_num:
        footer_parts.append(f"VAT Reg: {vat_num}")
    if co_email:
        footer_parts.append(co_email)
    elems.append(Paragraph(" · ".join(footer_parts), ST["small"]))
    elems.append(Paragraph(
        "This is a deposit invoice only. The balance will be invoiced on completion.",
        ST["small"]
    ))

    doc.build(elems)
    return buf.getvalue()
