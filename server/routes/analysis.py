"""Analysis API endpoints."""

from fastapi import APIRouter, HTTPException

from server.models.requests import AnalysisRequest
from server.models.responses import AnalysisResponse, AnalysisStartResponse
from server.services.analyzer import AnalysisOrchestrator

router = APIRouter()

# Shared orchestrator instance
orchestrator = AnalysisOrchestrator()


@router.post("/api/analyze", response_model=AnalysisStartResponse)
async def start_analysis(request: AnalysisRequest):
    """Start a new analysis (runs in background)."""
    analysis_id = await orchestrator.start_analysis(str(request.url))
    return AnalysisStartResponse(id=analysis_id)


@router.get("/api/results/{analysis_id}", response_model=AnalysisResponse)
async def get_results(analysis_id: str):
    """Get analysis results (or progress if still running)."""
    result = orchestrator.get_result(analysis_id)
    if not result:
        raise HTTPException(status_code=404, detail="Analysis not found")

    # Attach progress if still running
    if result.status == "running":
        result.progress = orchestrator.get_progress(analysis_id)

    return result
