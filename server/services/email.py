"""Resend email for lead capture."""

import logging

import resend

from server.config import settings

logger = logging.getLogger(__name__)


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
