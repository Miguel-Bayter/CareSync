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


class TestConfirmDose:
    def test_confirm_dose_returns_200(
        self, client: TestClient, enrolled_setup, db_session
    ) -> None:
        """POST /doses/{dose_id}/confirm should mark the dose as taken."""
        from uuid import UUID

        from sqlalchemy import select

        from app.models.dose import ScheduledDoseModel

        token, _, medication_id = enrolled_setup

        # Fetch the first scheduled dose directly from the test DB session
        stmt = select(ScheduledDoseModel).where(
            ScheduledDoseModel.medication_id == UUID(medication_id)
        )
        dose = db_session.scalars(stmt).first()
        assert dose is not None, "No doses were scheduled for the medication"

        response = client.post(
            f"{DOSES_URL}{dose.id}/confirm",
            json={"notes": "Taken with breakfast"},
            headers=_auth(token),
        )
        assert response.status_code == 200
        data = response.json()
        assert "dose_id" in data
        assert "remaining_stock" in data
        assert data["remaining_stock"] == 29  # 30 - 1

    def test_confirm_dose_twice_returns_409(
        self, client: TestClient, enrolled_setup, db_session
    ) -> None:
        """Confirming the same dose twice should return 409 Conflict."""
        from uuid import UUID

        from sqlalchemy import select

        from app.models.dose import ScheduledDoseModel

        token, _, medication_id = enrolled_setup
        stmt = select(ScheduledDoseModel).where(
            ScheduledDoseModel.medication_id == UUID(medication_id)
        )
        dose = db_session.scalars(stmt).first()

        client.post(
            f"{DOSES_URL}{dose.id}/confirm",
            json={},
            headers=_auth(token),
        )
        second_response = client.post(
            f"{DOSES_URL}{dose.id}/confirm",
            json={},
            headers=_auth(token),
        )
        assert second_response.status_code == 409

    def test_confirm_dose_without_auth_returns_401(
        self, client: TestClient, enrolled_setup, db_session
    ) -> None:
        """Unauthenticated confirm should return 401."""
        from uuid import UUID

        from sqlalchemy import select

        from app.models.dose import ScheduledDoseModel

        _, _, medication_id = enrolled_setup
        stmt = select(ScheduledDoseModel).where(
            ScheduledDoseModel.medication_id == UUID(medication_id)
        )
        dose = db_session.scalars(stmt).first()

        response = client.post(f"{DOSES_URL}{dose.id}/confirm", json={})
        assert response.status_code == 401


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
