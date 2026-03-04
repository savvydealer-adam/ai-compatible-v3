"""Lead capture endpoint."""

from fastapi import APIRouter

from server.models.requests import LeadRequest
from server.models.responses import LeadResponse
from server.services.email import send_lead_email

router = APIRouter()


@router.post("/api/leads", response_model=LeadResponse)
async def submit_lead(request: LeadRequest):
    """Submit lead capture form."""
    success = await send_lead_email(
        name=request.name,
        email=request.email,
        dealership=request.dealership,
        phone=request.phone,
        analysis_url=request.analysis_url,
        score=request.score,
    )
    return LeadResponse(
        success=success,
        message="Lead submitted successfully" if success else "Lead received (email not sent)",
    )
