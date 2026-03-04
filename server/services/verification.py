"""Verification store for lead-gated results."""

import logging
import secrets
import string
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

logger = logging.getLogger(__name__)

CODE_EXPIRY_MINUTES = 10


@dataclass
class VerificationRecord:
    analysis_id: str
    name: str
    email: str
    dealership: str
    phone: str
    method: str  # "email" or "sms"
    code: str = ""
    code_expires: datetime = field(default_factory=lambda: datetime.now(UTC))
    verified: bool = False
    verification_token: str = ""
    verified_emails: set[str] = field(default_factory=set)


class VerificationStore:
    def __init__(self) -> None:
        self._records: dict[str, VerificationRecord] = {}

    def create_or_update(
        self,
        analysis_id: str,
        name: str,
        email: str,
        dealership: str,
        phone: str,
        method: str,
    ) -> tuple[VerificationRecord, str]:
        """Create or update a verification record. Returns (record, code)."""
        code = "".join(secrets.choice(string.digits) for _ in range(6))
        expires = datetime.now(UTC) + timedelta(minutes=CODE_EXPIRY_MINUTES)

        existing = self._records.get(analysis_id)
        if existing:
            existing.name = name
            existing.email = email
            existing.dealership = dealership
            existing.phone = phone
            existing.method = method
            existing.code = code
            existing.code_expires = expires
            existing.verified = False
            existing.verification_token = ""
            logger.info("Updated verification for analysis %s", analysis_id)
            return existing, code

        record = VerificationRecord(
            analysis_id=analysis_id,
            name=name,
            email=email,
            dealership=dealership,
            phone=phone,
            method=method,
            code=code,
            code_expires=expires,
        )
        self._records[analysis_id] = record
        logger.info("Created verification for analysis %s", analysis_id)
        return record, code

    def verify_code(self, analysis_id: str, code: str) -> str | None:
        """Verify a code. Returns token on success, None on failure."""
        record = self._records.get(analysis_id)
        if not record:
            return None

        if record.code != code:
            return None

        if datetime.now(UTC) > record.code_expires:
            return None

        token = secrets.token_urlsafe(32)
        record.verified = True
        record.verification_token = token
        record.verified_emails.add(record.email)
        logger.info("Verified analysis %s via %s", analysis_id, record.method)
        return token

    def is_verified(self, analysis_id: str, token: str) -> bool:
        """Check if a token is valid for an analysis."""
        record = self._records.get(analysis_id)
        if not record:
            return False
        return record.verified and record.verification_token == token

    def get_record(self, analysis_id: str) -> VerificationRecord | None:
        """Get verification record for an analysis."""
        return self._records.get(analysis_id)


store = VerificationStore()
