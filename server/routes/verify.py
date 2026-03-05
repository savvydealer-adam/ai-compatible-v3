"""Verification endpoints for lead-gated results."""

import logging

from fastapi import APIRouter, HTTPException

from server.config import settings
from server.models.requests import VerifyConfirmModel, VerifyRequestModel
from server.models.responses import VerifyConfirmResponse, VerifyResponse
from server.routes.analysis import orchestrator
from server.services.email import send_lead_email, send_verification_email
from server.services.jwt_auth import AccountUser, create_jwt
from server.services.sms import send_verification_sms
from server.services.verification import store

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/api/verify/request", response_model=VerifyResponse)
async def request_verification(request: VerifyRequestModel):
    """Send a verification code via email or SMS."""
    result = orchestrator.get_result(request.analysis_id)
    if not result:
        raise HTTPException(status_code=404, detail="Analysis not found")
    if result.status != "complete":
        raise HTTPException(status_code=400, detail="Analysis not yet complete")

    record, code = store.create_or_update(
        analysis_id=request.analysis_id,
        name=request.name,
        email=request.email,
        dealership=request.dealership,
        phone=request.phone,
        method=request.method,
    )

    if request.method == "sms":
        if not request.phone:
            raise HTTPException(status_code=400, detail="Phone required for SMS verification")
        sent = await send_verification_sms(request.phone, code)
    else:
        sent = await send_verification_email(request.email, code)

    if not sent:
        raise HTTPException(status_code=500, detail="Failed to send verification code")

    return VerifyResponse(
        success=True,
        message=f"Verification code sent via {request.method}",
        method=request.method,
    )


@router.post("/api/verify/confirm", response_model=VerifyConfirmResponse)
async def confirm_verification(request: VerifyConfirmModel):
    """Verify a code and return an unlock token."""
    token = store.verify_code(request.analysis_id, request.code)
    if not token:
        return VerifyConfirmResponse(
            success=False,
            message="Invalid or expired code. Please try again.",
        )

    # Send lead notification to Adam
    record = store.get_record(request.analysis_id)
    if record:
        result = orchestrator.get_result(request.analysis_id)
        score = result.score.total_score if result and result.score else None
        await send_lead_email(
            name=record.name,
            email=record.email,
            dealership=record.dealership,
            phone=record.phone,
            analysis_url=result.url if result else "",
            score=score,
        )

    # Persist lead to database
    if record:
        try:
            from server.db import execute

            await execute(
                """
                INSERT INTO leads (analysis_id, name, email, dealership, phone, method, verified)
                VALUES ($1, $2, $3, $4, $5, $6, true)
                """,
                request.analysis_id,
                record.name,
                record.email,
                record.dealership,
                record.phone,
                record.method,
            )
        except Exception:
            logger.exception("Failed to save lead to database")

    # Issue JWT if account creation requested and JWT is configured
    account_jwt = ""
    if request.create_account and settings.jwt_secret and record:
        user = AccountUser(
            email=record.email,
            name=record.name,
            dealership=record.dealership,
            phone=record.phone,
        )
        account_jwt = create_jwt(user)

        # Persist account to database
        try:
            from server.db import execute

            await execute(
                """
                INSERT INTO accounts (email, name, dealership, phone, provider)
                VALUES ($1, $2, $3, $4, 'email')
                ON CONFLICT (email) DO UPDATE SET
                    name = EXCLUDED.name,
                    dealership = EXCLUDED.dealership,
                    phone = EXCLUDED.phone
                """,
                record.email,
                record.name,
                record.dealership,
                record.phone,
            )
        except Exception:
            logger.exception("Failed to save account to database")

    return VerifyConfirmResponse(
        success=True,
        token=token,
        jwt=account_jwt,
        message="Account created! All reports auto-unlocked."
        if account_jwt
        else "Verified! Full report unlocked.",
    )
