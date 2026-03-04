"""Analysis API endpoints."""

from fastapi import APIRouter, HTTPException, Query

from server.models.requests import AnalysisRequest
from server.models.responses import AnalysisResponse, AnalysisStartResponse, to_public_response
from server.services.analyzer import AnalysisOrchestrator
from server.services.verification import store as verification_store

router = APIRouter()

# Shared orchestrator instance
orchestrator = AnalysisOrchestrator()


@router.post("/api/analyze", response_model=AnalysisStartResponse)
async def start_analysis(request: AnalysisRequest):
    """Start a new analysis (runs in background)."""
    analysis_id = await orchestrator.start_analysis(str(request.url))
    return AnalysisStartResponse(id=analysis_id)


@router.get("/api/results/{analysis_id}", response_model=AnalysisResponse)
async def get_results(analysis_id: str, token: str = Query(default="")):
    """Get analysis results (or progress if still running)."""
    result = orchestrator.get_result(analysis_id)
    if not result:
        raise HTTPException(status_code=404, detail="Analysis not found")

    # Attach progress if still running
    if result.status == "running":
        result.progress = orchestrator.get_progress(analysis_id)
        return result

    # Gate completed results behind verification
    if result.status == "complete":
        if token and verification_store.is_verified(analysis_id, token):
            return result
        return to_public_response(result)

    return result
