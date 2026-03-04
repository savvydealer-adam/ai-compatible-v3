"""Twilio SMS verification."""

import logging
import re

from server.config import settings

logger = logging.getLogger(__name__)


def normalize_phone(phone: str) -> str:
    """Normalize phone number to E.164 format."""
    digits = re.sub(r"\D", "", phone)
    if len(digits) == 10:
        return f"+1{digits}"
    if len(digits) == 11 and digits.startswith("1"):
        return f"+{digits}"
    return f"+{digits}"


async def send_verification_sms(phone: str, code: str) -> bool:
    """Send verification code via Twilio SMS."""
    required = [
        settings.twilio_account_sid,
        settings.twilio_auth_token,
        settings.twilio_phone_number,
    ]
    if not all(required):
        logger.warning("Twilio not configured, skipping SMS")
        return False

    from twilio.rest import Client

    normalized = normalize_phone(phone)

    try:
        client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
        client.messages.create(
            body=f"Your AI Compatible verification code is: {code}",
            from_=settings.twilio_phone_number,
            to=normalized,
        )
        logger.info("Sent verification SMS to %s", normalized)
        return True
    except Exception:
        logger.exception("Failed to send verification SMS")
        return False
