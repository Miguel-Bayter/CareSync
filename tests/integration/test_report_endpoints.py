"""Integration tests for medical report endpoints."""

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"
PATIENTS_URL = "/api/v1/patients/"
MEDICATIONS_URL = "/api/v1/medications/"
REPORTS_URL = "/api/v1/reports/"


def _register_and_login(client: TestClient, email: str, password: str = "Password123") -> str:
    client.post(REGISTER_URL, json={"email": email, "password": password, "full_name": "Nurse Report"})
    resp = client.post(LOGIN_URL, json={"email": email, "password": password})
    return resp.json()["access_token"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def report_setup(client: TestClient):
    """Return (token, patient_id) with one enrolled medication."""
    token = _register_and_login(client, "report_nurse@example.com")
    patient_resp = client.post(
        PATIENTS_URL,
        json={
            "full_name": "Ana Milena Torres",
            "date_of_birth": "1950-06-15",
            "room_number": "305",
            "chronic_conditions": ["hypertension", "diabetes_type2"],
            "emergency_contact_name": "Luis Torres",
            "emergency_contact_phone": "+57 300 123 4567",
        },
        headers=_auth(token),
    )
    patient_id = patient_resp.json()["id"]
    client.post(
        MEDICATIONS_URL,
        json={
            "patient_id": patient_id,
            "generic_name": "metformin",
            "dose_mg": 850.0,
            "frequency_hours": 8,
            "with_food": True,
            "current_stock_units": 30,
            "minimum_stock_units": 5,
            "expiration_date": str(date.today() + timedelta(days=180)),
        },
        headers=_auth(token),
    )
    return token, patient_id


class TestMedicalPdfReport:
    def test_pdf_report_returns_200_with_pdf_content_type(
        self, client: TestClient, report_setup
    ) -> None:
        """GET /reports/{patient_id}/medical-pdf should return a PDF file."""
        token, patient_id = report_setup
        response = client.get(
            f"{REPORTS_URL}{patient_id}/medical-pdf",
            headers=_auth(token),
        )
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        assert "attachment" in response.headers["content-disposition"]
        assert len(response.content) > 0

    def test_pdf_report_without_auth_returns_401(
        self, client: TestClient, report_setup
    ) -> None:
        """PDF report endpoint should require authentication."""
        _, patient_id = report_setup
        response = client.get(f"{REPORTS_URL}{patient_id}/medical-pdf")
        assert response.status_code == 401

    def test_pdf_report_for_other_caregivers_patient_returns_403(
        self, client: TestClient, report_setup
    ) -> None:
        """Caregiver should not access another caregiver's patient report."""
        _, patient_id = report_setup
        other_token = _register_and_login(client, "other_report@example.com")
        response = client.get(
            f"{REPORTS_URL}{patient_id}/medical-pdf",
            headers=_auth(other_token),
        )
        assert response.status_code == 403
