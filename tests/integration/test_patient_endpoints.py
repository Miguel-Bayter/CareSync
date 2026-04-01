"""Integration tests for patient management endpoints."""


import pytest
from fastapi.testclient import TestClient

REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"
PATIENTS_URL = "/api/v1/patients/"


def _register_and_login(client: TestClient, email: str, password: str = "Password123") -> str:
    """Helper: register a caregiver and return the access token."""
    client.post(
        REGISTER_URL,
        json={"email": email, "password": password, "full_name": "Test Caregiver"},
    )
    resp = client.post(LOGIN_URL, json={"email": email, "password": password})
    return resp.json()["access_token"]


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def patient_payload() -> dict[str, object]:
    return {
        "full_name": "Rosa González Torres",
        "date_of_birth": "1952-06-15",
        "room_number": "101",
        "chronic_conditions": ["hypertension", "diabetes_type2"],
    }


class TestEnrollPatient:
    def test_enroll_patient_returns_201(
        self,
        client: TestClient,
        patient_payload: dict[str, object],
    ) -> None:
        """POST /patients/ should create a patient and return 201."""
        token = _register_and_login(client, "caregiver1@example.com")
        response = client.post(PATIENTS_URL, json=patient_payload, headers=_auth_headers(token))
        assert response.status_code == 201
        data = response.json()
        assert data["full_name"] == patient_payload["full_name"]
        assert "id" in data
        assert "age" in data
        assert data["age"] > 0


class TestGetPatientSummary:
    def test_get_patient_summary_returns_200(
        self,
        client: TestClient,
        patient_payload: dict[str, object],
    ) -> None:
        """GET /patients/{id}/summary should return the patient."""
        token = _register_and_login(client, "caregiver2@example.com")
        create_resp = client.post(PATIENTS_URL, json=patient_payload, headers=_auth_headers(token))
        patient_id = create_resp.json()["id"]

        response = client.get(f"{PATIENTS_URL}{patient_id}/summary", headers=_auth_headers(token))
        assert response.status_code == 200
        assert response.json()["id"] == patient_id

    def test_get_patient_of_another_caregiver_returns_403(
        self,
        client: TestClient,
        patient_payload: dict[str, object],
    ) -> None:
        """Another caregiver should not be able to read a patient they don't own."""
        token_owner = _register_and_login(client, "owner@example.com")
        token_other = _register_and_login(client, "other@example.com")

        create_resp = client.post(
            PATIENTS_URL, json=patient_payload, headers=_auth_headers(token_owner)
        )
        patient_id = create_resp.json()["id"]

        response = client.get(
            f"{PATIENTS_URL}{patient_id}/summary",
            headers=_auth_headers(token_other),
        )
        assert response.status_code == 403


class TestListPatients:
    def test_list_patients_returns_only_own_patients(
        self,
        client: TestClient,
        patient_payload: dict[str, object],
    ) -> None:
        """GET /patients/ should only return patients belonging to the caller."""
        token_a = _register_and_login(client, "caregiver_a@example.com")
        token_b = _register_and_login(client, "caregiver_b@example.com")

        # Caregiver A enrolls a patient
        client.post(PATIENTS_URL, json=patient_payload, headers=_auth_headers(token_a))

        # Caregiver B enrolls a different patient
        other_payload = {**patient_payload, "full_name": "Another Patient"}
        client.post(PATIENTS_URL, json=other_payload, headers=_auth_headers(token_b))

        response_a = client.get(PATIENTS_URL, headers=_auth_headers(token_a))
        assert response_a.status_code == 200
        names_a = [p["full_name"] for p in response_a.json()]
        assert patient_payload["full_name"] in names_a
        assert "Another Patient" not in names_a
