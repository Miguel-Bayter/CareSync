"""Unit tests for MedicationEnrollmentService."""

from datetime import date, timedelta
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.core.exceptions import ForbiddenError, NotFoundError
from app.schemas.medication import MedicationEnrollmentRequest
from app.services.medication_enrollment_service import MedicationEnrollmentService


def _make_request(patient_id=None, frequency_hours: int = 8) -> MedicationEnrollmentRequest:
    return MedicationEnrollmentRequest(
        patient_id=patient_id or uuid4(),
        generic_name="metformin",
        brand_name="Glucophage",
        dose_mg=500.0,
        frequency_hours=frequency_hours,
        with_food=True,
        current_stock_units=30,
        minimum_stock_units=5,
        expiration_date=date.today() + timedelta(days=180),
    )


def _make_service(patient=None):
    """Build the service with fully mocked repositories."""
    medication_repo = MagicMock()
    dose_repo = MagicMock()
    patient_repo = MagicMock()
    db = MagicMock()

    if patient is not None:
        patient_repo.find_by_id.return_value = patient

    service = MedicationEnrollmentService(
        medication_repo=medication_repo,
        dose_repo=dose_repo,
        patient_repo=patient_repo,
        db=db,
    )
    return service, medication_repo, dose_repo, patient_repo


class TestEnrollMedication:
    def test_raises_not_found_when_patient_missing(self) -> None:
        """Service must raise NotFoundError if patient does not exist."""
        service, _, _, patient_repo = _make_service()
        patient_repo.find_by_id.return_value = None
        caregiver_id = uuid4()

        with pytest.raises(NotFoundError):
            service.enroll_medication(_make_request(), caregiver_id)

    def test_raises_forbidden_when_patient_belongs_to_other_caregiver(self) -> None:
        """Service must raise ForbiddenError if patient belongs to a different caregiver."""
        patient = MagicMock()
        patient.caregiver_id = uuid4()  # different caregiver
        service, _, _, _ = _make_service(patient=patient)
        other_caregiver_id = uuid4()

        with pytest.raises(ForbiddenError):
            service.enroll_medication(_make_request(patient_id=uuid4()), other_caregiver_id)

    def test_schedules_correct_number_of_doses(self) -> None:
        """Every 8h for 30 days = 90 doses."""
        caregiver_id = uuid4()
        patient = MagicMock()
        patient.caregiver_id = caregiver_id

        service, medication_repo, dose_repo, _ = _make_service(patient=patient)

        # save() must assign an id to the entity so the service can build MedicationResponse
        def _assign_id(entity: object) -> object:
            entity.id = uuid4()  # type: ignore[attr-defined]
            return entity

        medication_repo.save.side_effect = _assign_id

        request = _make_request(frequency_hours=8)
        service.enroll_medication(request, caregiver_id)

        dose_repo.bulk_schedule.assert_called_once()
        doses = dose_repo.bulk_schedule.call_args[0][0]
        assert len(doses) == 90  # (30 * 24) // 8

    def test_schedules_doses_for_different_frequencies(self) -> None:
        """Every 24h for 30 days = 30 doses."""
        caregiver_id = uuid4()
        patient = MagicMock()
        patient.caregiver_id = caregiver_id

        service, medication_repo, dose_repo, _ = _make_service(patient=patient)

        def _assign_id(entity: object) -> object:
            entity.id = uuid4()  # type: ignore[attr-defined]
            return entity

        medication_repo.save.side_effect = _assign_id

        request = _make_request(frequency_hours=24)
        service.enroll_medication(request, caregiver_id)

        doses = dose_repo.bulk_schedule.call_args[0][0]
        assert len(doses) == 30  # (30 * 24) // 24
