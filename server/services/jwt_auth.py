"""JWT authentication for account users."""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import jwt

from server.config import settings

logger = logging.getLogger(__name__)


@dataclass
class AccountUser:
    email: str
    name: str
    dealership: str
    phone: str = ""


def create_jwt(user: AccountUser) -> str:
    """Create a signed JWT for an account user."""
    now = datetime.now(UTC)
    payload = {
        "sub": user.email,
        "name": user.name,
        "dealership": user.dealership,
        "phone": user.phone,
        "iat": now,
        "exp": now + timedelta(days=settings.jwt_expiry_days),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def decode_jwt(token: str) -> AccountUser | None:
    """Decode and validate a JWT. Returns None on expired/invalid."""
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        return AccountUser(
            email=payload["sub"],
            name=payload["name"],
            dealership=payload["dealership"],
            phone=payload.get("phone", ""),
        )
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None


def extract_bearer_token(authorization: str) -> str:
    """Extract token from 'Bearer <token>' header value."""
    if authorization.startswith("Bearer "):
        return authorization[7:]
    return ""
