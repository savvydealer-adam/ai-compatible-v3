"""Admin endpoints for @savvydealer.com users."""

import logging

from fastapi import APIRouter, Header, HTTPException, Query

from server import db
from server.services.jwt_auth import decode_jwt, extract_bearer_token

logger = logging.getLogger(__name__)

router = APIRouter()


def _require_admin(authorization: str) -> str:
    """Decode JWT and verify the email ends with @savvydealer.com. Returns email."""
    token = extract_bearer_token(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user = decode_jwt(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    if not user.email.endswith("@savvydealer.com"):
        raise HTTPException(status_code=403, detail="Admin access denied")

    return user.email


@router.get("/api/admin/stats")
async def admin_stats(authorization: str = Header(default="")):
    """Aggregate stats for the admin dashboard."""
    _require_admin(authorization)

    total_analyses = await db.fetchval("SELECT COUNT(*) FROM analyses") or 0
    total_leads = await db.fetchval("SELECT COUNT(*) FROM leads") or 0
    total_accounts = await db.fetchval("SELECT COUNT(*) FROM accounts") or 0
    avg_score = await db.fetchval(
        "SELECT ROUND(AVG(score)) FROM analyses WHERE score IS NOT NULL"
    )

    return {
        "total_analyses": total_analyses,
        "total_leads": total_leads,
        "total_accounts": total_accounts,
        "avg_score": int(avg_score) if avg_score is not None else None,
    }


@router.get("/api/admin/analyses")
async def admin_analyses(
    authorization: str = Header(default=""),
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
):
    """Paginated list of analyses."""
    _require_admin(authorization)

    rows = await db.fetch(
        """
        SELECT id, url, score, grade, status, error, created_at
        FROM analyses ORDER BY created_at DESC LIMIT $1 OFFSET $2
        """,
        limit,
        offset,
    )
    total = await db.fetchval("SELECT COUNT(*) FROM analyses") or 0

    return {
        "items": [dict(r) for r in rows],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/api/admin/analyses/{analysis_id}")
async def admin_analysis_detail(
    analysis_id: str,
    authorization: str = Header(default=""),
):
    """Full JSONB detail for one analysis."""
    _require_admin(authorization)

    row = await db.fetchrow(
        "SELECT id, url, score, grade, status, data_json, error, created_at "
        "FROM analyses WHERE id = $1",
        analysis_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Analysis not found")

    return dict(row)


@router.get("/api/admin/leads")
async def admin_leads(
    authorization: str = Header(default=""),
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
):
    """Paginated list of leads with joined analysis data."""
    _require_admin(authorization)

    rows = await db.fetch(
        """
        SELECT l.id, l.name, l.email, l.dealership, l.phone, l.method,
               l.verified, l.created_account, l.created_at,
               a.url AS analysis_url, a.score AS analysis_score
        FROM leads l
        LEFT JOIN analyses a ON l.analysis_id = a.id
        ORDER BY l.created_at DESC
        LIMIT $1 OFFSET $2
        """,
        limit,
        offset,
    )
    total = await db.fetchval("SELECT COUNT(*) FROM leads") or 0

    return {
        "items": [dict(r) for r in rows],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/api/admin/accounts")
async def admin_accounts(
    authorization: str = Header(default=""),
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
):
    """Paginated list of accounts."""
    _require_admin(authorization)

    rows = await db.fetch(
        """
        SELECT email, name, dealership, phone, provider, created_at
        FROM accounts ORDER BY created_at DESC LIMIT $1 OFFSET $2
        """,
        limit,
        offset,
    )
    total = await db.fetchval("SELECT COUNT(*) FROM accounts") or 0

    return {
        "items": [dict(r) for r in rows],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.delete("/api/admin/accounts/{email}")
async def admin_delete_account(
    email: str,
    authorization: str = Header(default=""),
):
    """Delete an account by email."""
    _require_admin(authorization)

    result = await db.execute("DELETE FROM accounts WHERE email = $1", email)
    if result == "DELETE 0":
        raise HTTPException(status_code=404, detail="Account not found")

    return {"success": True, "message": f"Account {email} deleted"}
