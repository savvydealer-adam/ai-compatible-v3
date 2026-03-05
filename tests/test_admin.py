"""Tests for admin endpoints."""

from unittest.mock import AsyncMock, patch

import jwt
import pytest
from fastapi.testclient import TestClient

from server.main import app

TEST_SECRET = "test-secret-key-for-unit-tests"


def _make_jwt(email: str, secret: str = TEST_SECRET) -> str:
    """Create a minimal JWT for testing."""
    from datetime import UTC, datetime, timedelta

    payload = {
        "sub": email,
        "name": "Test User",
        "dealership": "Test Motors",
        "phone": "",
        "iat": datetime.now(UTC),
        "exp": datetime.now(UTC) + timedelta(days=1),
    }
    return jwt.encode(payload, secret, algorithm="HS256")


@pytest.fixture
def test_client():
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture(autouse=True)
def _patch_jwt_secret():
    with patch("server.services.jwt_auth.settings") as mock_settings:
        mock_settings.jwt_secret = TEST_SECRET
        mock_settings.jwt_expiry_days = 30
        yield


class TestAdminAuth:
    def test_missing_jwt_returns_401(self, test_client):
        res = test_client.get("/api/admin/stats")
        assert res.status_code == 401

    def test_non_savvydealer_returns_403(self, test_client):
        token = _make_jwt("dealer@gmail.com")
        res = test_client.get(
            "/api/admin/stats",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 403

    def test_savvydealer_allowed(self, test_client):
        token = _make_jwt("adam@savvydealer.com")
        with patch("server.routes.admin.db") as mock_db:
            mock_db.fetchval = AsyncMock(return_value=0)
            res = test_client.get(
                "/api/admin/stats",
                headers={"Authorization": f"Bearer {token}"},
            )
        assert res.status_code == 200
        data = res.json()
        assert "total_analyses" in data
        assert "total_leads" in data
        assert "total_accounts" in data
        assert "avg_score" in data


class TestAdminEndpoints:
    @pytest.fixture(autouse=True)
    def _admin_token(self):
        self.token = _make_jwt("adam@savvydealer.com")
        self.headers = {"Authorization": f"Bearer {self.token}"}

    def test_analyses_list(self, test_client):
        with patch("server.routes.admin.db") as mock_db:
            mock_db.fetch = AsyncMock(return_value=[])
            mock_db.fetchval = AsyncMock(return_value=0)
            res = test_client.get("/api/admin/analyses", headers=self.headers)
        assert res.status_code == 200
        data = res.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_leads_list(self, test_client):
        with patch("server.routes.admin.db") as mock_db:
            mock_db.fetch = AsyncMock(return_value=[])
            mock_db.fetchval = AsyncMock(return_value=0)
            res = test_client.get("/api/admin/leads", headers=self.headers)
        assert res.status_code == 200
        assert res.json()["items"] == []

    def test_accounts_list(self, test_client):
        with patch("server.routes.admin.db") as mock_db:
            mock_db.fetch = AsyncMock(return_value=[])
            mock_db.fetchval = AsyncMock(return_value=0)
            res = test_client.get("/api/admin/accounts", headers=self.headers)
        assert res.status_code == 200
        assert res.json()["items"] == []

    def test_delete_account_not_found(self, test_client):
        with patch("server.routes.admin.db") as mock_db:
            mock_db.execute = AsyncMock(return_value="DELETE 0")
            res = test_client.delete(
                "/api/admin/accounts/nobody@test.com", headers=self.headers
            )
        assert res.status_code == 404

    def test_delete_account_success(self, test_client):
        with patch("server.routes.admin.db") as mock_db:
            mock_db.execute = AsyncMock(return_value="DELETE 1")
            res = test_client.delete(
                "/api/admin/accounts/user@test.com", headers=self.headers
            )
        assert res.status_code == 200
        assert res.json()["success"] is True

    def test_analysis_detail_not_found(self, test_client):
        with patch("server.routes.admin.db") as mock_db:
            mock_db.fetchrow = AsyncMock(return_value=None)
            res = test_client.get("/api/admin/analyses/abc123", headers=self.headers)
        assert res.status_code == 404
