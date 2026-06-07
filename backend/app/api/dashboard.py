"""
Operational Dashboard — internal protected endpoint.

GET /dashboard/summary   requires Clerk JWT

Returns structured operational state for both human-readable UI and
future agent consumption. All blocker codes and action keys are stable
identifiers that agents can use to decide next steps.
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload

from app.db import get_db
from app.models import Quote, RfqRequest

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

Db = Annotated[Session, Depends(get_db)]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _spec_fields(snap: dict | None) -> dict:
    """Handle both old flat snapshot and new nested questionnaire_answers format."""
    if not snap:
        return {}
    qa = snap.get("questionnaire_answers")
    if isinstance(qa, dict):
        return qa
    return snap


def _next_action_for(q: Quote) -> str | None:
    """Return the single most important next action message for a quote."""
    if q.status in ("lost", "expired", "converted"):
        return None
    if not q.total_inc_vat or float(q.total_inc_vat) == 0:
        return "Complete pricing"
    if q.status == "draft":
        return "Send to client"
    if q.status == "changes_requested":
        return "Review client requested changes"
    if q.status == "accepted":
        if q.payment_status not in ("deposit_received", "paid_in_full"):
            return "Generate deposit invoice / mark deposit received"
        if not q.pod_spec_id:
            return "Generate BOM"
    reqs = q.rfq_requests or []
    if reqs:
        pending = [r for r in reqs if r.status == "pending"]
        if pending:
            return f"Send RFQs to {len(pending)} supplier(s)"
        responded = [r for r in reqs if r.status == "responded"]
        awarded = [r for r in reqs if r.status == "awarded"]
        if responded and not awarded:
            return "Compare supplier responses and award"
        if awarded and q.payment_status in ("deposit_received", "paid_in_full"):
            return "Ready for production readiness review"
    return None


def _make_action(
    id_suffix: str,
    entity_id,
    reference: str,
    client_name: str | None,
    title: str,
    message: str,
    severity: str,
    blocker_code: str,
    recommended_action: str,
    action_key: str,
    requires_human: bool,
    can_suggest: bool,
    can_execute: bool,
    context: dict | None = None,
) -> dict:
    d = {
        "id": f"{entity_id}-{id_suffix}",
        "entity_type": "quote",
        "entity_id": str(entity_id),
        "reference": reference,
        "client_name": client_name or "Unknown",
        "title": title,
        "message": message,
        "severity": severity,
        "blocker_code": blocker_code,
        "recommended_action": recommended_action,
        "action_key": action_key,
        "action_url": f"/quotes/{entity_id}",
        "requires_human_approval": requires_human,
        "agent_can_suggest": can_suggest,
        "agent_can_execute": can_execute,
        "client_email": None,
        "pod_type": None,
        "dimensions": None,
        "price": None,
        "currency": "EUR",
        "lead_time": None,
        "delivery": None,
    }
    if context:
        d.update(context)
    return d


@router.get("/summary")
def get_dashboard_summary(db: Db):  # noqa: C901
    now = _now()

    # Load all quotes with rfq_requests eager-loaded (avoids N+1)
    quotes: list[Quote] = (
        db.query(Quote)
        .options(joinedload(Quote.rfq_requests))
        .order_by(Quote.created_at.desc())
        .all()
    )

    # ── Status counts ──────────────────────────────────────────────────────────

    counts: dict[str, int] = {
        "draft": 0, "sent": 0, "follow_up_due": 0, "changes_requested": 0,
        "accepted": 0, "lost": 0, "expired": 0, "converted": 0,
    }
    for q in quotes:
        s = q.status or "draft"
        counts[s] = counts.get(s, 0) + 1

    active_statuses = {"draft", "sent", "follow_up_due", "changes_requested", "accepted"}
    active_quotes = [q for q in quotes if q.status in active_statuses]

    seven_days_ago = now - timedelta(days=7)
    new_enquiries_count = sum(
        1 for q in quotes
        if q.lead_source == "website"
        and q.created_at
        and q.created_at.replace(tzinfo=timezone.utc) >= seven_days_ago
    )

    unpriced_count = sum(
        1 for q in active_quotes
        if not q.total_inc_vat or float(q.total_inc_vat) == 0
    )

    # Web enquiries with auto-estimate available but not yet manually priced
    estimate_available_count = sum(
        1 for q in active_quotes
        if q.lead_source == "website"
        and q.spec_snapshot
        and (q.spec_snapshot.get("pricing_estimate") or {}).get("status") == "estimated"
        and (not q.total_inc_vat or float(q.total_inc_vat) == 0)
    )

    # Draft quotes that have pricing and are ready to send
    ready_to_send_count = sum(
        1 for q in active_quotes
        if q.status == "draft"
        and q.total_inc_vat
        and float(q.total_inc_vat) > 0
    )

    # Web enquiries missing dimensions (can't auto-price)
    input_incomplete_count = sum(
        1 for q in active_quotes
        if q.status == "draft"
        and q.lead_source == "website"
        and q.spec_snapshot
        and not _spec_fields(q.spec_snapshot).get("width_m")
        and not _spec_fields(q.spec_snapshot).get("length_m")
    )

    awaiting_deposit_count = sum(
        1 for q in quotes
        if q.status == "accepted"
        and q.payment_status in (None, "awaiting_deposit")
        and q.total_inc_vat is not None
        and float(q.total_inc_vat) > 0
    )

    # Sent quotes past their follow_up_at date (but not yet followed up / responded)
    follow_up_due_count = sum(
        1 for q in quotes
        if q.status == "sent"
        and q.follow_up_at
        and q.follow_up_at.replace(tzinfo=timezone.utc) <= now
        and not q.client_responded_at
    )

    # Per-quote RFQ aggregates
    rfq_awaiting_response = 0
    rfq_responded = 0
    rfq_awarded = 0
    for q in active_quotes:
        reqs = q.rfq_requests or []
        if not reqs:
            continue
        statuses = {r.status for r in reqs}
        if "awarded" in statuses:
            rfq_awarded += 1
        elif "responded" in statuses:
            rfq_responded += 1
        elif statuses & {"pending", "viewed"}:
            rfq_awaiting_response += 1

    # ── Summary cards ─────────────────────────────────────────────────────────

    summary_cards = [
        {"key": "new_enquiries",        "label": "New enquiries (7d)",       "count": new_enquiries_count,                                        "severity": "info"},
        {"key": "input_incomplete",     "label": "Incomplete input",         "count": input_incomplete_count, "severity": "info" if input_incomplete_count == 0 else "warning"},
        {"key": "estimate_available",   "label": "Estimates ready",          "count": estimate_available_count,                                   "severity": "info"},
        {"key": "ready_to_send",        "label": "Ready to send",            "count": ready_to_send_count,    "severity": "info" if ready_to_send_count == 0     else "warning"},
        {"key": "unpriced_quotes",      "label": "Unpriced",                 "count": unpriced_count,         "severity": "warning" if unpriced_count > 0        else "info"},
        {"key": "changes_requested",    "label": "Changes requested",        "count": counts["changes_requested"], "severity": "warning" if counts["changes_requested"] > 0 else "info"},
        {"key": "accepted_quotes",      "label": "Accepted",                 "count": counts["accepted"],                                         "severity": "info"},
        {"key": "awaiting_deposit",     "label": "Awaiting deposit",         "count": awaiting_deposit_count, "severity": "warning" if awaiting_deposit_count > 0 else "info"},
        {"key": "rfq_awaiting_response","label": "RFQs awaiting response",   "count": rfq_awaiting_response,                                      "severity": "info"},
        {"key": "follow_up_due",        "label": "Follow-up due",            "count": follow_up_due_count,    "severity": "warning" if follow_up_due_count > 0 else "info"},
    ]

    # ── Action required ────────────────────────────────────────────────────────

    action_required = []

    for q in quotes:
        if q.status in ("lost", "expired", "converted"):
            continue

        reqs = q.rfq_requests or []
        ref = q.quote_number or str(q.id)[:8]
        cn = q.client_name

        _fields = _spec_fields(q.spec_snapshot)
        _w, _l = _fields.get("width_m"), _fields.get("length_m")
        _h = _fields.get("height_m") or _fields.get("wall_height_m")
        _dims = (f"{_w}m × {_l}m" + (f" × {_h}m H" if _h else "")) if _w and _l else None
        _ctx = {
            "client_email": q.client_email,
            "pod_type": _fields.get("pod_type"),
            "dimensions": _dims,
            "price": float(q.total_inc_vat) if q.total_inc_vat and float(q.total_inc_vat) > 0 else None,
            "currency": q.currency,
            "lead_time": _fields.get("lead_time"),
            "delivery": _fields.get("delivery_install_option"),
        }

        def add(suffix, title, message, severity, blocker_code, recommended, action_key,
                requires_human=False, can_suggest=True, can_execute=False):
            action_required.append(_make_action(
                suffix, q.id, ref, cn, title, message, severity, blocker_code,
                recommended, action_key, requires_human, can_suggest, can_execute,
                context=_ctx,
            ))

        # QUOTE_INPUT_INCOMPLETE — web enquiry missing dimensions
        if (q.status == "draft"
                and q.lead_source == "website"
                and q.spec_snapshot):
            if not _fields.get("width_m") and not _fields.get("length_m"):
                add("input-incomplete",
                    "Enquiry missing dimensions",
                    f"{ref}: web enquiry received but no dimensions provided — cannot auto-price.",
                    "info", "QUOTE_INPUT_INCOMPLETE",
                    "Contact client to confirm dimensions and update the enquiry",
                    "open_quote", can_suggest=True)

        # QUOTE_ESTIMATE_USED — auto-estimate available but no manual pricing yet
        if (q.lead_source == "website"
                and q.spec_snapshot
                and (q.spec_snapshot.get("pricing_estimate") or {}).get("status") == "estimated"
                and (not q.total_inc_vat or float(q.total_inc_vat) == 0)):
            pe = q.spec_snapshot["pricing_estimate"]
            est_total = pe.get("total_inc_vat", 0)
            add("estimate-available",
                "Auto-estimate ready — review and confirm pricing",
                f"{ref}: indicative estimate €{est_total:,.0f} inc VAT generated from enquiry answers.",
                "info", "QUOTE_ESTIMATE_USED",
                f"Review estimate (€{est_total:,.0f} inc VAT) and confirm or revise pricing",
                "open_quote", can_suggest=True)

        # QUOTE_READY_TO_SEND — priced but still in draft
        if q.status == "draft" and q.total_inc_vat and float(q.total_inc_vat) > 0:
            add("ready-to-send",
                "Quote ready to send to client",
                f"{ref}: priced at {q.currency} {float(q.total_inc_vat):,.0f} but still in draft.",
                "info", "QUOTE_READY_TO_SEND",
                "Review and send quote to client",
                "open_quote", can_suggest=True)

        # QUOTE_DOCUMENTS_NOT_GENERATED — sent but no client portal link
        if q.status in ("sent", "follow_up_due") and not getattr(q, "client_token", None):
            add("no-client-link",
                "No client portal link",
                f"{ref}: marked as sent but client portal link not generated.",
                "info", "QUOTE_DOCUMENTS_NOT_GENERATED",
                "Generate client quote portal link so client can view and respond",
                "open_quote", can_execute=True)

        # FOLLOW_UP_DUE — sent quote past follow-up date with no client response
        if (q.status == "sent"
                and q.follow_up_at
                and q.follow_up_at.replace(tzinfo=timezone.utc) <= now
                and not q.client_responded_at):
            days_overdue = (now - q.follow_up_at.replace(tzinfo=timezone.utc)).days
            add("follow-up-due",
                "Follow-up due",
                f"{ref}: sent {days_overdue + 3}+ days ago with no client response. Follow up now.",
                "warning", "FOLLOW_UP_DUE",
                "Contact client to follow up on the quote",
                "open_quote", requires_human=True)

        # QUOTE_PRICE_MISSING
        if q.status in ("draft", "sent", "follow_up_due") and (not q.total_inc_vat or float(q.total_inc_vat) == 0):
            add("pricing",
                "Quote missing price",
                f"{ref}: created from enquiry but has no calculated price.",
                "warning", "QUOTE_PRICE_MISSING",
                "Complete pricing or run estimate calculation",
                "open_quote")

        # CLIENT_CHANGES_REQUESTED
        if q.status == "changes_requested":
            add("changes",
                "Client requested changes",
                f"{ref}: client requested changes via portal. Review and update.",
                "warning", "CLIENT_CHANGES_REQUESTED",
                "Review requested changes and revise the quote",
                "open_quote", requires_human=True)

        # DEPOSIT_NOT_PAID
        if (q.status == "accepted"
                and q.total_inc_vat is not None and float(q.total_inc_vat) > 0
                and q.payment_status in (None, "awaiting_deposit")):
            add("deposit",
                "Deposit not paid",
                f"{ref}: accepted but deposit not yet received.",
                "warning", "DEPOSIT_NOT_PAID",
                "Send deposit invoice and follow up payment",
                "open_quote")

        # DEPOSIT_INVOICE_MISSING (accepted + priced + no deposit config)
        if (q.status == "accepted"
                and q.total_inc_vat is not None and float(q.total_inc_vat) > 0
                and q.deposit_percent is None
                and q.payment_status is None):
            add("deposit-invoice",
                "Deposit invoice not configured",
                f"{ref}: accepted with pricing but deposit % not set.",
                "info", "DEPOSIT_INVOICE_MISSING",
                "Set deposit percentage and generate deposit invoice",
                "open_quote", can_execute=True)

        # BOM_NOT_GENERATED
        if q.status == "accepted" and q.pod_spec_id is None:
            add("bom",
                "BOM not generated",
                f"{ref}: accepted but no pod spec or BOM linked.",
                "warning", "BOM_NOT_GENERATED",
                "Create pod spec and generate BOM",
                "open_quote", requires_human=True)

        # RFQ_NOT_SENT
        pending_rfqs = [r for r in reqs if r.status == "pending"]
        if pending_rfqs:
            add("rfq-not-sent",
                f"RFQ not sent ({len(pending_rfqs)} supplier{'s' if len(pending_rfqs) > 1 else ''})",
                f"{ref}: RFQ created but not yet sent to suppliers.",
                "info", "RFQ_NOT_SENT",
                "Send RFQ links to suppliers",
                "open_rfq", can_execute=True)

        # SUPPLIER_RESPONSE_PENDING
        viewed_rfqs = [r for r in reqs if r.status == "viewed"]
        if viewed_rfqs and not any(r.status in ("responded", "awarded") for r in reqs):
            add("rfq-pending",
                f"Awaiting supplier response ({len(viewed_rfqs)} viewed)",
                f"{ref}: suppliers have opened RFQ but not yet responded.",
                "info", "SUPPLIER_RESPONSE_PENDING",
                "Follow up with suppliers",
                "open_rfq")

        # SUPPLIER_AWARD_MISSING
        responded_rfqs = [r for r in reqs if r.status == "responded"]
        awarded_rfqs = [r for r in reqs if r.status == "awarded"]
        if responded_rfqs and not awarded_rfqs:
            add("award",
                f"Responses received — no award ({len(responded_rfqs)} responded)",
                f"{ref}: {len(responded_rfqs)} supplier(s) responded. Compare and award.",
                "warning", "SUPPLIER_AWARD_MISSING",
                "Compare supplier responses and award preferred supplier",
                "open_rfq", requires_human=True)

        # READY_FOR_PRODUCTION_REVIEW
        if (q.status == "accepted"
                and awarded_rfqs
                and q.payment_status in ("deposit_received", "paid_in_full")):
            add("production",
                "Ready for production review",
                f"{ref}: supplier awarded and deposit received. Ready to start.",
                "info", "READY_FOR_PRODUCTION_REVIEW",
                "Initiate production readiness review",
                "open_quote", requires_human=True)

    # Sort: blocked → error → warning → info
    _sev = {"blocked": 0, "error": 1, "warning": 2, "info": 3}
    action_required.sort(key=lambda x: _sev.get(x["severity"], 4))

    # ── Recent enquiries ───────────────────────────────────────────────────────

    recent_enquiries = []
    for q in quotes[:20]:
        fields = _spec_fields(q.spec_snapshot)
        w = fields.get("width_m")
        l = fields.get("length_m")
        recent_enquiries.append({
            "quote_id":           str(q.id),
            "reference":          q.quote_number or str(q.id)[:8],
            "client_name":        q.client_name or "Unknown",
            "product_template_id": q.spec_snapshot.get("product_template_id") if q.spec_snapshot else None,
            "pod_type":           fields.get("pod_type"),
            "dimensions":         f"{w}m × {l}m" if w and l else None,
            "status":             q.status,
            "lead_source":        q.lead_source,
            "pricing_status":     "complete" if (q.total_inc_vat and float(q.total_inc_vat) > 0) else "missing",
            "total_inc_vat":      float(q.total_inc_vat) if q.total_inc_vat else None,
            "currency":           q.currency,
            "created_at":         q.created_at.isoformat() if q.created_at else None,
            "next_action":        _next_action_for(q),
        })

    # ── Pricing health ─────────────────────────────────────────────────────────

    pricing_health = {
        "complete":      sum(1 for q in active_quotes if q.total_inc_vat and float(q.total_inc_vat) > 0),
        "missing_price": sum(1 for q in active_quotes if not q.total_inc_vat or float(q.total_inc_vat) == 0),
        "no_bom":        sum(1 for q in active_quotes if q.pod_spec_id is None),
        "has_bom":       sum(1 for q in active_quotes if q.pod_spec_id is not None),
    }

    # ── BOM / RFQ health ──────────────────────────────────────────────────────

    bom_rfq_health = {
        "no_bom":                    pricing_health["no_bom"],
        "has_bom":                   pricing_health["has_bom"],
        "rfq_not_sent":              sum(
            1 for q in active_quotes
            if any(r.status == "pending" for r in (q.rfq_requests or []))
        ),
        "rfq_awaiting_response":     rfq_awaiting_response,
        "supplier_responses_received": rfq_responded,
        "supplier_award_missing":    sum(
            1 for q in active_quotes
            if any(r.status == "responded" for r in (q.rfq_requests or []))
            and not any(r.status == "awarded" for r in (q.rfq_requests or []))
        ),
        "supplier_awards_complete":  rfq_awarded,
    }

    # ── Payment status ─────────────────────────────────────────────────────────

    payment_status = {
        "accepted_no_payment_status": sum(
            1 for q in quotes
            if q.status == "accepted"
            and q.payment_status is None
            and q.total_inc_vat is not None
            and float(q.total_inc_vat) > 0
        ),
        "awaiting_deposit":   awaiting_deposit_count,
        "deposit_received":   sum(1 for q in quotes if q.payment_status == "deposit_received"),
        "paid_in_full":       sum(1 for q in quotes if q.payment_status == "paid_in_full"),
        "overdue":            sum(1 for q in quotes if q.payment_status == "overdue"),
    }

    # ── Document status (recent 10 quotes) ────────────────────────────────────

    document_status = []
    for q in quotes[:10]:
        has_pricing = q.total_inc_vat is not None and float(q.total_inc_vat) > 0
        has_deposit_config = has_pricing and q.deposit_percent is not None
        has_bom = q.pod_spec_id is not None
        rfq_reqs = q.rfq_requests or []
        document_status.append({
            "quote_id":    str(q.id),
            "reference":   q.quote_number or str(q.id)[:8],
            "client_name": q.client_name or "Unknown",
            "status":      q.status,
            "documents": {
                "deposit_invoice_pdf": "on_demand"     if has_deposit_config else "not_applicable",
                "bom":                 "available"     if has_bom            else "not_applicable",
                "rfq_json":            "available"     if rfq_reqs           else "not_applicable",
                "client_quote_pdf":    "not_applicable",
            },
        })

    # ── Next actions (system-level) ────────────────────────────────────────────

    next_actions = []
    if counts["changes_requested"] > 0:
        next_actions.append({"priority": 1, "action": "Review client-requested changes",          "count": counts["changes_requested"],             "blocker_code": "CLIENT_CHANGES_REQUESTED"})
    if follow_up_due_count > 0:
        next_actions.append({"priority": 2, "action": "Follow up on sent quotes",                 "count": follow_up_due_count,                     "blocker_code": "FOLLOW_UP_DUE"})
    if awaiting_deposit_count > 0:
        next_actions.append({"priority": 3, "action": "Follow up deposit payments",               "count": awaiting_deposit_count,                  "blocker_code": "DEPOSIT_NOT_PAID"})
    if ready_to_send_count > 0:
        next_actions.append({"priority": 4, "action": "Send priced quotes to clients",            "count": ready_to_send_count,                     "blocker_code": "QUOTE_READY_TO_SEND"})
    if estimate_available_count > 0:
        next_actions.append({"priority": 5, "action": "Review and confirm auto-estimates",        "count": estimate_available_count,                "blocker_code": "QUOTE_ESTIMATE_USED"})
    if input_incomplete_count > 0:
        next_actions.append({"priority": 6, "action": "Follow up incomplete enquiries (no dims)", "count": input_incomplete_count,                  "blocker_code": "QUOTE_INPUT_INCOMPLETE"})
    if unpriced_count > 0:
        next_actions.append({"priority": 7, "action": "Complete pricing for unpriced quotes",     "count": unpriced_count,                          "blocker_code": "QUOTE_PRICE_MISSING"})
    if bom_rfq_health["supplier_award_missing"] > 0:
        next_actions.append({"priority": 8, "action": "Compare supplier responses and award",     "count": bom_rfq_health["supplier_award_missing"], "blocker_code": "SUPPLIER_AWARD_MISSING"})
    if bom_rfq_health["rfq_not_sent"] > 0:
        next_actions.append({"priority": 9, "action": "Send pending RFQs to suppliers",           "count": bom_rfq_health["rfq_not_sent"],           "blocker_code": "RFQ_NOT_SENT"})

    # ── Agent-readable state ───────────────────────────────────────────────────

    open_action_count = len(action_required)
    blocked_count = sum(1 for a in action_required if a["severity"] in ("error", "blocked"))
    severities = [a["severity"] for a in action_required]

    if "blocked" in severities:   highest_severity = "blocked"
    elif "error" in severities:   highest_severity = "error"
    elif "warning" in severities: highest_severity = "warning"
    elif "info" in severities:    highest_severity = "info"
    else:                         highest_severity = "none"

    if open_action_count == 0:              system_status = "healthy"
    elif highest_severity in ("error", "blocked"): system_status = "critical"
    else:                                   system_status = "needs_attention"

    if counts["changes_requested"] > 0:         recommended_focus = "client_changes"
    elif follow_up_due_count > 0:              recommended_focus = "follow_up_sent_quotes"
    elif awaiting_deposit_count > 0:            recommended_focus = "deposit_and_payments"
    elif ready_to_send_count > 0:               recommended_focus = "send_quotes"
    elif estimate_available_count > 0:          recommended_focus = "confirm_estimates"
    elif input_incomplete_count > 0:            recommended_focus = "follow_up_enquiries"
    elif unpriced_count > 0:                    recommended_focus = "pricing_and_quotes"
    elif bom_rfq_health["supplier_award_missing"] > 0: recommended_focus = "supplier_awards"
    elif bom_rfq_health["rfq_not_sent"] > 0:   recommended_focus = "rfq_management"
    else:                                       recommended_focus = "none"

    agent_readable_state = {
        "generated_at":            now.isoformat(),
        "system_status":           system_status,
        "highest_severity":        highest_severity,
        "open_action_count":       open_action_count,
        "blocked_count":           blocked_count,
        "recommended_focus":       recommended_focus,
        "quote_counts":            counts,
        "active_quote_count":      len(active_quotes),
        "input_incomplete_count":   input_incomplete_count,
        "estimate_available_count": estimate_available_count,
        "ready_to_send_count":      ready_to_send_count,
        "follow_up_due_count":      follow_up_due_count,
    }

    return {
        "summary_cards":      summary_cards,
        "action_required":    action_required,
        "recent_enquiries":   recent_enquiries,
        "pricing_health":     pricing_health,
        "bom_rfq_health":     bom_rfq_health,
        "payment_status":     payment_status,
        "document_status":    document_status,
        "next_actions":       next_actions,
        "agent_readable_state": agent_readable_state,
    }
