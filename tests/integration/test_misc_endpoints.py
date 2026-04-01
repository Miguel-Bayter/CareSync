"""Integration tests for miscellaneous endpoints and auth edge cases."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"
MEDICATIONS_URL = "/api/v1/medications/"
PATIENTS_URL = "/api/v1/patients/"


def _register_and_login(client: TestClient, email: str, password: str = "Password123") -> str:
    client.post(REGISTER_URL, json={"email": email, "password": password, "full_name": "Nurse"})
    resp = client.post(LOGIN_URL, json={"email": email, "password": password})
    return resp.json()["access_token"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


class TestHealthEndpoint:
    def test_health_returns_200(self, client: TestClient) -> None:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


class TestAuthDependencyEdgeCases:
    def test_invalid_token_returns_401(self, client: TestClient) -> None:
        """A syntactically valid bearer token that fails JWT decode triggers line 37."""
        response = client.get(
            PATIENTS_URL,
            headers={"Authorization": "Bearer invalid.token.value"},
        )
        assert response.status_code == 401

    def test_token_for_nonexistent_user_returns_401(self, client: TestClient) -> None:
        """A valid JWT whose subject UUID isn't in the DB triggers line 46."""
        from app.core.security import create_access_token
        from uuid import uuid4

        # Create token for a UUID that was never registered
        ghost_token = create_access_token(str(uuid4()))
        response = client.get(
            PATIENTS_URL,
            headers=_auth(ghost_token),
        )
        assert response.status_code == 401


class TestCriticalStockEdgeCases:
    def _setup(self, client: TestClient, email: str):
        token = _register_and_login(client, email)
        patient_resp = client.post(
            PATIENTS_URL,
            json={
                "full_name": "Juan Perez",
                "date_of_birth": "1945-03-10",
                "room_number": "302",
                "chronic_conditions": [],
            },
            headers=_auth(token),
        )
        return token, patient_resp.json()["id"]

    def test_critical_stock_unknown_patient_returns_404(self, client: TestClient) -> None:
        """GET /medications/critical-stock with unknown patient_id → 404 (line 117)."""
        from uuid import uuid4
        token = _register_and_login(client, "stock404@example.com")
        response = client.get(
            f"{MEDICATIONS_URL}critical-stock",
            params={"patient_id": str(uuid4())},
            headers=_auth(token),
        )
        assert response.status_code == 404

    def test_critical_stock_other_caregivers_patient_returns_403(self, client: TestClient) -> None:
        """GET /medications/critical-stock with another caregiver's patient → 403 (line 119)."""
        _, patient_id = self._setup(client, "owner_stock@example.com")
        other_token = _register_and_login(client, "intruder_stock@example.com")
        response = client.get(
            f"{MEDICATIONS_URL}critical-stock",
            params={"patient_id": patient_id},
            headers=_auth(other_token),
        )
        assert response.status_code == 403


class TestLoggingConfigProductionBranch:
    def test_production_logging_does_not_raise(self) -> None:
        """setup_logging() with is_development=False uses JSON renderer (line 29)."""
        from app.core.logging_config import setup_logging

        with patch("app.core.logging_config.settings") as mock_settings:
            mock_settings.is_development = False
            # Must complete without error
            setup_logging()
