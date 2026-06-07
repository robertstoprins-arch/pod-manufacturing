"""
Email service abstraction.

Supported providers (checked in order):
  1. Resend  — set RESEND_API_KEY in environment
  2. Logged  — no provider configured; email body is logged to stdout and
               returned with status="logged_not_sent" so nothing is silently lost.

Usage:
    from app.api.email_service import send_email
    result = send_email(to="client@example.com", subject="...", text_body="...")
    if result.status != "sent":
        # handle gracefully — the endpoint should still mark the quote as sent
        # but should return email_status so the user knows
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field

import httpx

logger = logging.getLogger(__name__)


@dataclass
class EmailResult:
    status: str                     # "sent" | "logged_not_sent" | "error"
    provider: str | None = None     # "resend" | None
    message: str = ""
    message_id: str | None = None
    error_detail: str | None = None


def send_email(
    to: str,
    subject: str,
    html_body: str,
    text_body: str | None = None,
    reply_to: str | None = None,
    from_name: str = "Top-R Solutions",
) -> EmailResult:
    """
    Send an email via the configured provider.
    If no provider is configured, the email is logged (not silently dropped).
    """
    resend_key = os.environ.get("RESEND_API_KEY", "").strip()
    from_email  = os.environ.get("EMAIL_FROM", "quotes@top-r.com").strip()

    if resend_key:
        return _send_via_resend(
            to=to,
            subject=subject,
            html_body=html_body,
            text_body=text_body,
            from_addr=f"{from_name} <{from_email}>",
            reply_to=reply_to,
            api_key=resend_key,
        )

    # ── No provider ───────────────────────────────────────────────────────────
    logger.warning(
        "[EMAIL NOT SENT — no provider configured]\n"
        "  Set RESEND_API_KEY in environment to enable delivery.\n"
        "  To:      %s\n"
        "  Subject: %s\n"
        "  ---\n%s",
        to, subject, text_body or "(html only)",
    )
    return EmailResult(
        status="logged_not_sent",
        provider=None,
        message=(
            "Email provider not configured — RESEND_API_KEY is not set. "
            "The email body has been logged to backend stdout. "
            "Set RESEND_API_KEY in Render environment variables to enable delivery."
        ),
    )


def _send_via_resend(
    to: str,
    subject: str,
    html_body: str,
    text_body: str | None,
    from_addr: str,
    reply_to: str | None,
    api_key: str,
) -> EmailResult:
    try:
        payload: dict = {
            "from":    from_addr,
            "to":      [to],
            "subject": subject,
            "html":    html_body,
        }
        if text_body:
            payload["text"] = text_body
        if reply_to:
            payload["reply_to"] = reply_to

        resp = httpx.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type":  "application/json",
            },
            json=payload,
            timeout=15,
        )

        if resp.status_code in (200, 201):
            data = resp.json()
            return EmailResult(
                status="sent",
                provider="resend",
                message="Email sent successfully",
                message_id=data.get("id"),
            )

        err_msg = resp.json().get("message", resp.text) if resp.headers.get("content-type", "").startswith("application/json") else resp.text
        logger.error("Resend API returned %s: %s", resp.status_code, err_msg)
        return EmailResult(
            status="error",
            provider="resend",
            message=f"Resend API error ({resp.status_code})",
            error_detail=err_msg,
        )

    except httpx.TimeoutException:
        logger.error("Resend API timed out")
        return EmailResult(status="error", provider="resend", message="Email send timed out. Check Resend dashboard.")
    except Exception as exc:
        logger.exception("Unexpected error sending email via Resend")
        return EmailResult(status="error", provider="resend", message="Unexpected error", error_detail=str(exc))
