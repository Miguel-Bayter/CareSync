"""Integration tests for authentication endpoints."""

import pytest
from fastapi.testclient import TestClient

REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"
PATIENTS_URL = "/api/v1/patients/"


@pytest.fixture()
def registration_payload() -> dict[str, str]:
    return {
        "email": "rosa@example.com",
        "password": "Password123",
        "full_name": "Rosa González",
    }


class TestRegisterEndpoint:
    def test_register_returns_201(self, client: TestClient, registration_payload: dict[str, str]) -> None:
        """POST /auth/register should return 201 with the created caregiver."""
        response = client.post(REGISTER_URL, json=registration_payload)
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == registration_payload["email"]
        assert data["full_name"] == registration_payload["full_name"]
        assert "id" in data
        assert "hashed_password" not in data

    def test_register_duplicate_email_returns_409(
        self, client: TestClient, registration_payload: dict[str, str]
    ) -> None:
        """Registering the same e-mail twice should return 409."""
        client.post(REGISTER_URL, json=registration_payload)
        response = client.post(REGISTER_URL, json=registration_payload)
        assert response.status_code == 409


class TestLoginEndpoint:
    def test_login_returns_jwt_token(self, client: TestClient, registration_payload: dict[str, str]) -> None:
        """POST /auth/login should return a valid bearer token."""
        client.post(REGISTER_URL, json=registration_payload)
        response = client.post(
            LOGIN_URL,
            json={"email": registration_payload["email"], "password": registration_payload["password"]},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password_returns_422(self, client: TestClient, registration_payload: dict[str, str]) -> None:
        """POST /auth/login with wrong password should return error."""
        client.post(REGISTER_URL, json=registration_payload)
        response = client.post(
            LOGIN_URL,
            json={"email": registration_payload["email"], "password": "WrongPass999"},
        )
        assert response.status_code in (401, 422)

    def test_protected_endpoint_requires_auth(self, client: TestClient) -> None:
        """GET /patients/ without a token should return 401."""
        response = client.get(PATIENTS_URL)
        assert response.status_code == 401
