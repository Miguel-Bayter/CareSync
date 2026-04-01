"""Integration tests for medication endpoints."""

from datetime import date, timedelta
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"
PATIENTS_URL = "/api/v1/patients/"
MEDICATIONS_URL = "/api/v1/medications/"


def _register_and_login(client: TestClient, email: str, password: str = "Password123") -> str:
    client.post(REGISTER_URL, json={"email": email, "password": password, "full_name": "Nurse Test"})
    resp = client.post(LOGIN_URL, json={"email": email, "password": password})
    return resp.json()["access_token"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def caregiver_with_patient(client: TestClient):
    """Return (token, patient_id) for a registered caregiver with one patient."""
    token = _register_and_login(client, "med_nurse@example.com")
    patient_resp = client.post(
        PATIENTS_URL,
        json={
            "full_name": "Rosa González",
            "date_of_birth": "1952-06-15",
            "room_number": "201",
            "chronic_conditions": ["hypertension"],
        },
        headers=_auth(token),
    )
    return token, patient_resp.json()["id"]


@pytest.fixture()
def medication_payload(caregiver_with_patient):
    token, patient_id = caregiver_with_patient
    return token, patient_id, {
        "patient_id": patient_id,
        "generic_name": "metformin",
        "brand_name": "Glucophage",
        "dose_mg": 500.0,
        "frequency_hours": 8,
        "with_food": True,
        "current_stock_units": 30,
        "minimum_stock_units": 5,
        "expiration_date": str(date.today() + timedelta(days=180)),
    }


class TestEnrollMedication:
    def test_enroll_medication_returns_201(
        self, client: TestClient, medication_payload
    ) -> None:
        """POST /medications/ should create a medication and schedule doses."""
        token, _, payload = medication_payload
        response = client.post(MEDICATIONS_URL, json=payload, headers=_auth(token))
        assert response.status_code == 201
        data = response.json()
        assert data["generic_name"] == "metformin"
        assert data["doses_scheduled"] == 90  # (30*24) // 8

    def test_enroll_medication_without_auth_returns_401(
        self, client: TestClient, medication_payload
    ) -> None:
        """POST /medications/ without token should return 401."""
        _, _, payload = medication_payload
        response = client.post(MEDICATIONS_URL, json=payload)
        assert response.status_code == 401

    def test_enroll_medication_for_another_caregivers_patient_returns_403(
        self, client: TestClient, medication_payload
    ) -> None:
        """A caregiver should not enroll a medication for another caregiver's patient."""
        _, _patient_id, payload = medication_payload
        # Register a second caregiver and use their token
        other_token = _register_and_login(client, "other_nurse@example.com")
        response = client.post(MEDICATIONS_URL, json=payload, headers=_auth(other_token))
        assert response.status_code == 403

    def test_expiration_date_in_past_returns_422(
        self, client: TestClient, medication_payload
    ) -> None:
        """Medication with past expiration date should fail domain validation."""
        token, _, payload = medication_payload
        payload = {**payload, "expiration_date": "2020-01-01"}
        response = client.post(MEDICATIONS_URL, json=payload, headers=_auth(token))
        assert response.status_code == 422


class TestGetCriticalStock:
    def test_critical_stock_returns_medication_near_minimum(
        self, client: TestClient, medication_payload
    ) -> None:
        """Medication with stock at minimum should appear in critical stock list."""
        token, patient_id, payload = medication_payload
        # current_stock_units == minimum_stock_units triggers critical flag
        payload = {**payload, "current_stock_units": 5, "minimum_stock_units": 5}
        client.post(MEDICATIONS_URL, json=payload, headers=_auth(token))

        response = client.get(
            f"{MEDICATIONS_URL}critical-stock",
            params={"patient_id": patient_id},
            headers=_auth(token),
        )
        assert response.status_code == 200
        assert len(response.json()) >= 1


class TestDrugInteractions:
    def test_interactions_returns_200_with_mocked_fda(
        self, client: TestClient, medication_payload
    ) -> None:
        """GET /medications/{patient_id}/interactions should return reports."""
        token, patient_id, payload = medication_payload
        client.post(MEDICATIONS_URL, json=payload, headers=_auth(token))

        with patch(
            "app.services.drug_interaction_service._fetch_interactions_from_fda",
            return_value="May interact with insulin.",
        ):
            response = client.get(
                f"{MEDICATIONS_URL}{patient_id}/interactions",
                headers=_auth(token),
            )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert data[0]["medication_name"] == "metformin"
        assert "insulin" in data[0]["interaction_text"]
