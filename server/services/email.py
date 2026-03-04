"""Resend email for lead capture."""

import logging

import resend

from server.config import settings

logger = logging.getLogger(__name__)


async def send_verification_email(email: str, code: str) -> bool:
    """Send verification code email via Resend."""
    if not settings.resend_api_key:
        logger.warning("RESEND_API_KEY not configured, skipping verification email")
        return False

    resend.api_key = settings.resend_api_key

    wrapper = "font-family:Arial,sans-serif;max-width:480px;margin:0 auto;padding:32px"
    code_box = (
        "background:#f4f4f8;border-radius:12px;padding:24px;text-align:center;margin-bottom:24px"
    )
    code_style = "font-size:36px;font-weight:bold;letter-spacing:8px;color:#1a1a2e"
    body = (
        f'<div style="{wrapper}">'
        '<h2 style="color:#1a1a2e;margin-bottom:8px">'
        "Verification Code</h2>"
        '<p style="color:#555;margin-bottom:24px">'
        "Enter this code to unlock your full AI compatibility report:"
        "</p>"
        f'<div style="{code_box}">'
        f'<span style="{code_style}">{code}</span>'
        "</div>"
        '<p style="color:#888;font-size:13px">'
        "This code expires in 10 minutes."
        "</p></div>"
    )

    try:
        resend.Emails.send(
            {
                "from": "AI Compatible <noreply@savvydealer.com>",
                "to": [email],
                "subject": f"Your verification code: {code}",
                "html": body,
            }
        )
        return True
    except Exception:
        logger.exception("Failed to send verification email")
        return False


async def send_lead_email(
    name: str,
    email: str,
    dealership: str,
    phone: str = "",
    analysis_url: str = "",
    score: int | None = None,
) -> bool:
    """Send lead capture notification email via Resend."""
    if not settings.resend_api_key:
        logger.warning("RESEND_API_KEY not configured, skipping email")
        return False

    resend.api_key = settings.resend_api_key

    body = f"""
    <h2>New AI Compatibility Lead</h2>
    <p><strong>Name:</strong> {name}</p>
    <p><strong>Email:</strong> {email}</p>
    <p><strong>Dealership:</strong> {dealership}</p>
    <p><strong>Phone:</strong> {phone or "Not provided"}</p>
    <p><strong>Analysis URL:</strong> {analysis_url or "Not provided"}</p>
    <p><strong>Score:</strong> {score if score is not None else "N/A"}</p>
    """

    try:
        resend.Emails.send(
            {
                "from": "AI Compatible <noreply@savvydealer.com>",
                "to": ["adam@savvydealer.com"],
                "subject": f"New AI Compatibility Lead: {dealership}",
                "html": body,
            }
        )
        return True
    except Exception:
        logger.exception("Failed to send lead email")
        return False
