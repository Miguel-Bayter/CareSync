"""Unit tests for ElderlyPatientService."""

from datetime import UTC, date, datetime
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.core.exceptions import ForbiddenError, PatientNotFoundError
from app.domain.enums import ChronicCondition
from app.schemas.patient import ElderlyPatientEnrollmentRequest
from app.services.patient_service import ElderlyPatientService


class _FakePatient:
    """Minimal patient-like object that Pydantic can validate via from_attributes."""

    def __init__(self, caregiver_id=None):
        self.id = uuid4()
        self.full_name = "Rosa González Torres"
        self.date_of_birth = date(1952, 6, 15)
        self.room_number = "101"
        self.chronic_conditions = ["hypertension"]
        self.caregiver_id = caregiver_id or uuid4()
        self.created_at = datetime.now(UTC)


def _make_service():
    repo = MagicMock()
    db = MagicMock()
    return ElderlyPatientService(patient_repo=repo, db=db), repo


def _enrollment_request() -> ElderlyPatientEnrollmentRequest:
    return ElderlyPatientEnrollmentRequest(
        full_name="Rosa González Torres",
        date_of_birth=date(1952, 6, 15),
        room_number="101",
        chronic_conditions=[ChronicCondition.HYPERTENSION],
    )


class TestEnrollPatient:
    def test_enroll_patient_returns_summary(self) -> None:
        service, repo = _make_service()
        caregiver_id = uuid4()
        saved_patient = _FakePatient(caregiver_id=caregiver_id)
        repo.save.return_value = saved_patient

        result = service.enroll_patient(_enrollment_request(), caregiver_id)

        repo.save.assert_called_once()
        assert result.full_name == saved_patient.full_name
        assert result.caregiver_id == caregiver_id

    def test_enroll_patient_assigns_correct_caregiver_id(self) -> None:
        service, repo = _make_service()
        caregiver_id = uuid4()
        repo.save.return_value = _FakePatient(caregiver_id=caregiver_id)

        service.enroll_patient(_enrollment_request(), caregiver_id)

        saved_model = repo.save.call_args[0][0]
        assert saved_model.caregiver_id == caregiver_id


class TestGetPatientSummary:
    def test_raises_not_found_when_patient_missing(self) -> None:
        service, repo = _make_service()
        repo.find_by_id.return_value = None

        with pytest.raises(PatientNotFoundError):
            service.get_patient_summary(uuid4(), uuid4())

    def test_raises_forbidden_when_wrong_caregiver(self) -> None:
        service, repo = _make_service()
        patient = _FakePatient(caregiver_id=uuid4())
        repo.find_by_id.return_value = patient

        with pytest.raises(ForbiddenError):
            service.get_patient_summary(patient.id, uuid4())  # different caregiver

    def test_returns_summary_for_correct_caregiver(self) -> None:
        service, repo = _make_service()
        caregiver_id = uuid4()
        patient = _FakePatient(caregiver_id=caregiver_id)
        repo.find_by_id.return_value = patient

        result = service.get_patient_summary(patient.id, caregiver_id)

        assert str(result.id) == str(patient.id)
        assert result.full_name == patient.full_name


class TestListPatients:
    def test_returns_all_caregiver_patients(self) -> None:
        service, repo = _make_service()
        caregiver_id = uuid4()
        patients = [_FakePatient(caregiver_id=caregiver_id) for _ in range(3)]
        repo.find_all_by_caregiver_id.return_value = patients

        result = service.list_patients(caregiver_id)

        assert len(result) == 3
        repo.find_all_by_caregiver_id.assert_called_once_with(caregiver_id)

    def test_returns_empty_list_when_no_patients(self) -> None:
        service, repo = _make_service()
        repo.find_all_by_caregiver_id.return_value = []

        result = service.list_patients(uuid4())

        assert result == []
