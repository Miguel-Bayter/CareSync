"""Integration tests for dose tracking endpoints."""

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"
PATIENTS_URL = "/api/v1/patients/"
MEDICATIONS_URL = "/api/v1/medications/"
DOSES_URL = "/api/v1/doses/"


def _register_and_login(client: TestClient, email: str, password: str = "Password123") -> str:
    client.post(REGISTER_URL, json={"email": email, "password": password, "full_name": "Nurse Dose"})
    resp = client.post(LOGIN_URL, json={"email": email, "password": password})
    return resp.json()["access_token"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def enrolled_setup(client: TestClient):
    """Return (token, patient_id, medication_id) ready for dose tests."""
    token = _register_and_login(client, "dose_nurse@example.com")

    patient_resp = client.post(
        PATIENTS_URL,
        json={
            "full_name": "Pedro Sánchez Ruiz",
            "date_of_birth": "1948-03-22",
            "room_number": "305",
            "chronic_conditions": ["diabetes_type2"],
        },
        headers=_auth(token),
    )
    patient_id = patient_resp.json()["id"]

    med_resp = client.post(
        MEDICATIONS_URL,
        json={
            "patient_id": patient_id,
            "generic_name": "lisinopril",
            "dose_mg": 10.0,
            "frequency_hours": 24,
            "with_food": False,
            "current_stock_units": 30,
            "minimum_stock_units": 5,
            "expiration_date": str(date.today() + timedelta(days=365)),
        },
        headers=_auth(token),
    )
    medication_id = med_resp.json()["id"]
    return token, patient_id, medication_id


class TestAdherenceReport:
    def test_adherence_returns_200_with_medications(
        self, client: TestClient, enrolled_setup
    ) -> None:
        """GET /doses/adherence/{patient_id} should return adherence stats."""
        token, patient_id, _ = enrolled_setup
        response = client.get(
            f"{DOSES_URL}adherence/{patient_id}",
            headers=_auth(token),
        )
        assert response.status_code == 200
        data = response.json()
        assert data["patient_id"] == patient_id
        assert "overall_adherence" in data
        assert isinstance(data["medications"], list)
        assert len(data["medications"]) == 1
        assert data["medications"][0]["generic_name"] == "lisinopril"

    def test_adherence_for_other_caregivers_patient_returns_403(
        self, client: TestClient, enrolled_setup
    ) -> None:
        """Caregiver should not access another caregiver's patient adherence."""
        _, patient_id, _ = enrolled_setup
        other_token = _register_and_login(client, "other_dose@example.com")
        response = client.get(
            f"{DOSES_URL}adherence/{patient_id}",
            headers=_auth(other_token),
        )
        assert response.status_code == 403
