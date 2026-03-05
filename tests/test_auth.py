"""Tests for JWT authentication."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import jwt
import pytest
from fastapi.testclient import TestClient

from server.main import app
from server.services.jwt_auth import AccountUser, create_jwt, decode_jwt, extract_bearer_token

TEST_SECRET = "test-secret-key-for-unit-tests"
TEST_GOOGLE_CLIENT_ID = "test-client-id.apps.googleusercontent.com"


@pytest.fixture(autouse=True)
def _jwt_secret():
    """Set a test JWT secret for all tests in this module."""
    with patch("server.services.jwt_auth.settings") as mock_settings:
        mock_settings.jwt_secret = TEST_SECRET
        mock_settings.jwt_expiry_days = 30
        yield


@pytest.fixture
def client():
    """TestClient for the FastAPI app."""
    return TestClient(app)


class TestJwtRoundtrip:
    def test_create_and_decode(self):
        user = AccountUser(
            email="john@test.com",
            name="John Doe",
            dealership="Test Motors",
            phone="5551234567",
        )
        token = create_jwt(user)
        decoded = decode_jwt(token)

        assert decoded is not None
        assert decoded.email == "john@test.com"
        assert decoded.name == "John Doe"
        assert decoded.dealership == "Test Motors"
        assert decoded.phone == "5551234567"

    def test_roundtrip_without_phone(self):
        user = AccountUser(email="jane@test.com", name="Jane", dealership="Jane Motors")
        token = create_jwt(user)
        decoded = decode_jwt(token)

        assert decoded is not None
        assert decoded.email == "jane@test.com"
        assert decoded.phone == ""


class TestJwtExpiry:
    def test_expired_token_rejected(self):
        payload = {
            "sub": "expired@test.com",
            "name": "Expired",
            "dealership": "Old Motors",
            "phone": "",
            "iat": datetime.now(UTC) - timedelta(days=60),
            "exp": datetime.now(UTC) - timedelta(days=1),
        }
        token = jwt.encode(payload, TEST_SECRET, algorithm="HS256")
        result = decode_jwt(token)
        assert result is None


class TestJwtSecurity:
    def test_wrong_secret_rejected(self):
        user = AccountUser(email="a@b.com", name="A", dealership="B")
        token = create_jwt(user)

        # Try decoding with wrong secret
        with patch("server.services.jwt_auth.settings") as mock_settings:
            mock_settings.jwt_secret = "wrong-secret"
            mock_settings.jwt_expiry_days = 30
            result = decode_jwt(token)
            assert result is None

    def test_garbage_token_rejected(self):
        assert decode_jwt("not.a.jwt") is None
        assert decode_jwt("") is None
        assert decode_jwt("garbage") is None

    def test_tampered_payload_rejected(self):
        user = AccountUser(email="a@b.com", name="A", dealership="B")
        token = create_jwt(user)
        parts = token.split(".")
        # Tamper with payload
        parts[1] = parts[1][::-1]
        tampered = ".".join(parts)
        assert decode_jwt(tampered) is None


class TestExtractBearerToken:
    def test_valid_bearer(self):
        assert extract_bearer_token("Bearer abc123") == "abc123"

    def test_no_prefix(self):
        assert extract_bearer_token("abc123") == ""

    def test_empty(self):
        assert extract_bearer_token("") == ""

    def test_just_bearer(self):
        assert extract_bearer_token("Bearer ") == ""


class TestGoogleAuth:
    def test_missing_credential(self, client):
        """Missing credential field returns 422."""
        res = client.post("/api/auth/google", json={"dealership": "Test Motors"})
        assert res.status_code == 422

    def test_invalid_google_token(self, client):
        """Invalid Google credential returns 401."""
        with patch("server.routes.auth.settings") as mock_settings:
            mock_settings.google_oauth_client_id = TEST_GOOGLE_CLIENT_ID
            mock_settings.jwt_secret = TEST_SECRET
            res = client.post(
                "/api/auth/google",
                json={
                    "credential": "invalid.token.here",
                    "dealership": "Test Motors",
                    "phone": "5551234567",
                },
            )
            assert res.status_code == 401
            assert "Invalid Google credential" in res.json()["detail"]

    def test_valid_google_flow(self, client):
        """Valid Google token creates account and returns JWT."""
        fake_idinfo = {
            "email": "dealer@gmail.com",
            "name": "Test Dealer",
            "sub": "google-uid-123",
        }
        with (
            patch("server.routes.auth.settings") as mock_settings,
            patch(
                "server.routes.auth.google_id_token.verify_oauth2_token",
                return_value=fake_idinfo,
            ),
            patch("server.routes.auth.send_lead_email", new_callable=AsyncMock) as mock_email,
        ):
            mock_settings.google_oauth_client_id = TEST_GOOGLE_CLIENT_ID
            mock_settings.jwt_secret = TEST_SECRET
            mock_settings.jwt_expiry_days = 30

            res = client.post(
                "/api/auth/google",
                json={
                    "credential": "valid.google.token",
                    "dealership": "Test Motors",
                    "phone": "5551234567",
                },
            )
            assert res.status_code == 200
            data = res.json()
            assert "jwt" in data
            assert data["jwt"]

            # Verify the JWT decodes correctly
            decoded = decode_jwt(data["jwt"])
            assert decoded is not None
            assert decoded.email == "dealer@gmail.com"
            assert decoded.name == "Test Dealer"
            assert decoded.dealership == "Test Motors"
            assert decoded.phone == "5551234567"

            # Verify lead email was sent
            mock_email.assert_called_once_with(
                name="Test Dealer",
                email="dealer@gmail.com",
                dealership="Test Motors",
                phone="5551234567",
            )

    def test_google_oauth_not_configured(self, client):
        """Returns 500 if Google OAuth client ID is not set."""
        with patch("server.routes.auth.settings") as mock_settings:
            mock_settings.google_oauth_client_id = ""
            mock_settings.jwt_secret = TEST_SECRET
            res = client.post(
                "/api/auth/google",
                json={
                    "credential": "some.token",
                    "dealership": "Test Motors",
                },
            )
            assert res.status_code == 500
