"""Health check endpoint."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/api/health")
async def health():
    return {"status": "ok", "version": "3.0.0"}
