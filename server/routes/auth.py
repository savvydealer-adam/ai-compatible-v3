"""Auth endpoints for account users."""

import logging

from fastapi import APIRouter, Header, HTTPException
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token

from server.config import settings
from server.models.requests import GoogleAuthRequest
from server.models.responses import AuthMeResponse
from server.services.email import send_lead_email
from server.services.jwt_auth import AccountUser, create_jwt, decode_jwt, extract_bearer_token

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/api/auth/me", response_model=AuthMeResponse)
async def auth_me(authorization: str = Header(default="")):
    """Return the current user from JWT."""
    token = extract_bearer_token(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user = decode_jwt(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    return AuthMeResponse(
        email=user.email,
        name=user.name,
        dealership=user.dealership,
        phone=user.phone,
    )


@router.post("/api/auth/refresh")
async def auth_refresh(authorization: str = Header(default="")):
    """Validate JWT and return a fresh one with extended expiry."""
    token = extract_bearer_token(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user = decode_jwt(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    if not settings.jwt_secret:
        raise HTTPException(status_code=500, detail="JWT not configured")

    new_token = create_jwt(user)
    return {"jwt": new_token}


@router.post("/api/auth/google")
async def google_auth(request: GoogleAuthRequest):
    """Authenticate via Google ID token, create account, and return JWT."""
    if not settings.google_oauth_client_id:
        raise HTTPException(status_code=500, detail="Google OAuth not configured")
    if not settings.jwt_secret:
        raise HTTPException(status_code=500, detail="JWT not configured")

    try:
        idinfo = google_id_token.verify_oauth2_token(
            request.credential,
            google_requests.Request(),
            settings.google_oauth_client_id,
        )
    except ValueError as err:
        raise HTTPException(status_code=401, detail="Invalid Google credential") from err

    email = idinfo.get("email", "")
    name = idinfo.get("name", "")
    if not email:
        raise HTTPException(status_code=401, detail="Google account has no email")

    user = AccountUser(
        email=email,
        name=name,
        dealership=request.dealership,
        phone=request.phone,
    )
    jwt_token = create_jwt(user)

    await send_lead_email(
        name=name,
        email=email,
        dealership=request.dealership,
        phone=request.phone,
    )

    # Persist account and lead to database
    try:
        from server.db import execute

        await execute(
            """
            INSERT INTO accounts (email, name, dealership, phone, provider)
            VALUES ($1, $2, $3, $4, 'google')
            ON CONFLICT (email) DO UPDATE SET
                name = EXCLUDED.name,
                dealership = EXCLUDED.dealership,
                phone = EXCLUDED.phone
            """,
            email,
            name,
            request.dealership,
            request.phone,
        )
        await execute(
            """
            INSERT INTO leads (name, email, dealership, phone, method, verified, created_account)
            VALUES ($1, $2, $3, $4, 'google', true, true)
            """,
            name,
            email,
            request.dealership,
            request.phone,
        )
    except Exception:
        logger.exception("Failed to save Google auth to database")

    return {"jwt": jwt_token}
