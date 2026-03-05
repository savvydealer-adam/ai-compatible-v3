"""Tests for verification service and gated results."""

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from server.models.responses import AnalysisResponse, ScoreResponse, to_public_response
from server.services.verification import VerificationStore

# --- VerificationStore unit tests ---


class TestVerificationStore:
    def setup_method(self):
        self.store = VerificationStore()

    def test_create_record(self):
        record, code = self.store.create_or_update(
            analysis_id="abc123",
            name="John",
            email="john@test.com",
            dealership="Test Motors",
            phone="5551234567",
            method="email",
        )
        assert record.analysis_id == "abc123"
        assert record.name == "John"
        assert record.email == "john@test.com"
        assert record.method == "email"
        assert len(code) == 6
        assert code.isdigit()
        assert not record.verified

    def test_update_existing_record(self):
        _, code1 = self.store.create_or_update(
            analysis_id="abc123",
            name="John",
            email="john@test.com",
            dealership="Test Motors",
            phone="",
            method="email",
        )
        _, code2 = self.store.create_or_update(
            analysis_id="abc123",
            name="Jane",
            email="jane@test.com",
            dealership="New Motors",
            phone="5559999999",
            method="sms",
        )
        record = self.store.get_record("abc123")
        assert record is not None
        assert record.name == "Jane"
        assert record.email == "jane@test.com"
        assert record.method == "sms"
        # Codes should differ (extremely high probability)
        # But we test that update works, not randomness

    def test_verify_correct_code(self):
        _, code = self.store.create_or_update(
            analysis_id="abc123",
            name="John",
            email="john@test.com",
            dealership="Test Motors",
            phone="",
            method="email",
        )
        token = self.store.verify_code("abc123", code)
        assert token is not None
        assert len(token) > 0

    def test_verify_wrong_code(self):
        self.store.create_or_update(
            analysis_id="abc123",
            name="John",
            email="john@test.com",
            dealership="Test Motors",
            phone="",
            method="email",
        )
        token = self.store.verify_code("abc123", "000000")
        assert token is None

    def test_verify_expired_code(self):
        _, code = self.store.create_or_update(
            analysis_id="abc123",
            name="John",
            email="john@test.com",
            dealership="Test Motors",
            phone="",
            method="email",
        )
        # Manually expire the code
        record = self.store.get_record("abc123")
        record.code_expires = datetime.now(UTC) - timedelta(minutes=1)

        token = self.store.verify_code("abc123", code)
        assert token is None

    def test_verify_nonexistent_analysis(self):
        token = self.store.verify_code("nonexistent", "123456")
        assert token is None

    def test_is_verified_with_valid_token(self):
        _, code = self.store.create_or_update(
            analysis_id="abc123",
            name="John",
            email="john@test.com",
            dealership="Test Motors",
            phone="",
            method="email",
        )
        token = self.store.verify_code("abc123", code)
        assert self.store.is_verified("abc123", token)

    def test_is_verified_with_wrong_token(self):
        _, code = self.store.create_or_update(
            analysis_id="abc123",
            name="John",
            email="john@test.com",
            dealership="Test Motors",
            phone="",
            method="email",
        )
        self.store.verify_code("abc123", code)
        assert not self.store.is_verified("abc123", "wrong-token")

    def test_is_verified_nonexistent(self):
        assert not self.store.is_verified("nonexistent", "any-token")

    def test_verified_emails_tracked(self):
        _, code = self.store.create_or_update(
            analysis_id="abc123",
            name="John",
            email="john@test.com",
            dealership="Test Motors",
            phone="",
            method="email",
        )
        self.store.verify_code("abc123", code)
        record = self.store.get_record("abc123")
        assert "john@test.com" in record.verified_emails


# --- to_public_response tests ---


class TestToPublicResponse:
    def _make_response(self) -> AnalysisResponse:
        return AnalysisResponse(
            id="test-id",
            url="https://example.com",
            status="complete",
            score=ScoreResponse(
                total_score=85,
                max_score=100,
                grade="B",
                grade_label="Good",
                categories=[],
                bonus_points=0,
            ),
            bot_permissions=[],
            issues=[{"severity": "warning", "category": "test", "message": "test issue"}],
            recommendations=["Fix something"],
            analysis_time=42.5,
        )

    def test_gated_flag_set(self):
        response = self._make_response()
        public = to_public_response(response)
        assert public.gated is True

    def test_score_preserved(self):
        response = self._make_response()
        public = to_public_response(response)
        assert public.score is not None
        assert public.score.total_score == 85
        assert public.score.grade == "B"

    def test_analysis_time_stripped(self):
        response = self._make_response()
        public = to_public_response(response)
        assert public.analysis_time is None

    def test_categories_stripped(self):
        response = self._make_response()
        public = to_public_response(response)
        assert public.score.categories == []
        assert public.score.bonus_points == 0

    def test_detailed_fields_stripped(self):
        response = self._make_response()
        public = to_public_response(response)
        assert public.blocking is None
        assert public.bot_permissions == []
        assert public.issues == []
        assert public.recommendations == []
        assert public.inventory is None
        assert public.vdp is None
        assert public.sitemap is None

    def test_id_and_url_preserved(self):
        response = self._make_response()
        public = to_public_response(response)
        assert public.id == "test-id"
        assert public.url == "https://example.com"
        assert public.status == "complete"


# --- API endpoint tests ---


class TestVerifyEndpoints:
    @pytest.fixture
    def client(self):
        from server.main import app

        return TestClient(app)

    def test_request_verify_missing_analysis(self, client):
        res = client.post(
            "/api/verify/request",
            json={
                "analysis_id": "nonexistent",
                "name": "John",
                "email": "john@test.com",
                "dealership": "Test Motors",
                "method": "email",
            },
        )
        assert res.status_code == 404

    def test_confirm_invalid_code(self, client):
        res = client.post(
            "/api/verify/confirm",
            json={"analysis_id": "nonexistent", "code": "123456"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is False

    def test_verify_request_invalid_method(self, client):
        res = client.post(
            "/api/verify/request",
            json={
                "analysis_id": "test",
                "name": "John",
                "email": "john@test.com",
                "dealership": "Test Motors",
                "method": "carrier_pigeon",
            },
        )
        assert res.status_code == 422


# --- Gated results endpoint tests ---


class TestGatedResults:
    @pytest.fixture
    def client(self):
        from server.main import app

        return TestClient(app)

    @patch("server.routes.analysis.orchestrator")
    def test_complete_results_are_gated_without_token(self, mock_orch, client):
        mock_orch.get_result.return_value = AnalysisResponse(
            id="test-id",
            url="https://example.com",
            status="complete",
            score=ScoreResponse(
                total_score=90,
                max_score=100,
                grade="A",
                grade_label="Excellent",
            ),
            issues=[{"severity": "info", "category": "test", "message": "msg"}],
            analysis_time=30.0,
        )

        res = client.get("/api/results/test-id")
        assert res.status_code == 200
        data = res.json()
        assert data["gated"] is True
        assert data["score"]["total_score"] == 90
        assert data["issues"] == []

    @patch("server.routes.analysis.orchestrator")
    @patch("server.routes.analysis.verification_store")
    def test_complete_results_unlocked_with_valid_token(self, mock_store, mock_orch, client):
        mock_orch.get_result.return_value = AnalysisResponse(
            id="test-id",
            url="https://example.com",
            status="complete",
            score=ScoreResponse(
                total_score=90,
                max_score=100,
                grade="A",
                grade_label="Excellent",
            ),
            issues=[{"severity": "info", "category": "test", "message": "msg"}],
            analysis_time=30.0,
        )
        mock_store.is_verified.return_value = True

        res = client.get("/api/results/test-id?token=valid-token")
        assert res.status_code == 200
        data = res.json()
        assert data["gated"] is False
        assert len(data["issues"]) == 1

    @patch("server.routes.analysis.orchestrator")
    def test_running_results_not_gated(self, mock_orch, client):
        mock_orch.get_result.return_value = AnalysisResponse(
            id="test-id",
            url="https://example.com",
            status="running",
        )
        mock_orch.get_progress.return_value = {"step": "Testing bots", "percent": 50}

        res = client.get("/api/results/test-id")
        assert res.status_code == 200
        data = res.json()
        assert data["gated"] is False
        assert data["progress"]["percent"] == 50
