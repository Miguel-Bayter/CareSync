"""Unit tests for DoseTrackingService."""

from datetime import UTC, datetime
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.core.exceptions import DoseAlreadyConfirmedError, DoseNotFoundError, ForbiddenError
from app.domain.enums import DoseStatus
from app.services.dose_tracking_service import DoseTrackingService


def _make_service():
    dose_repo = MagicMock()
    medication_repo = MagicMock()
    alert_repo = MagicMock()
    db = MagicMock()
    service = DoseTrackingService(
        dose_repo=dose_repo,
        medication_repo=medication_repo,
        alert_repo=alert_repo,
        db=db,
    )
    return service, dose_repo, medication_repo, alert_repo


def _make_dose(status: str = DoseStatus.PENDING.value) -> MagicMock:
    dose = MagicMock()
    dose.id = uuid4()
    dose.medication_id = uuid4()
    dose.status = status
    dose.taken_at = None
    dose.notes = None
    return dose


def _make_medication(caregiver_id, stock: int = 10, minimum: int = 3) -> MagicMock:
    med = MagicMock()
    med.id = uuid4()
    med.patient_id = uuid4()
    med.generic_name = "metformin"
    med.current_stock_units = stock
    med.minimum_stock_units = minimum
    med.patient = MagicMock()
    med.patient.caregiver_id = caregiver_id
    return med


class TestConfirmDoseTaken:
    def test_raises_not_found_when_dose_missing(self) -> None:
        service, dose_repo, _, _ = _make_service()
        dose_repo.find_by_id.return_value = None

        with pytest.raises(DoseNotFoundError):
            service.confirm_dose_taken(dose_id=uuid4(), caregiver_id=uuid4())

    def test_raises_forbidden_when_wrong_caregiver(self) -> None:
        service, dose_repo, medication_repo, _ = _make_service()
        caregiver_id = uuid4()
        dose = _make_dose()
        medication = _make_medication(caregiver_id=uuid4())  # different caregiver
        dose_repo.find_by_id.return_value = dose
        medication_repo.find_by_id.return_value = medication

        with pytest.raises(ForbiddenError):
            service.confirm_dose_taken(dose_id=dose.id, caregiver_id=caregiver_id)

    def test_raises_conflict_when_already_confirmed(self) -> None:
        service, dose_repo, medication_repo, _ = _make_service()
        caregiver_id = uuid4()
        dose = _make_dose(status=DoseStatus.CONFIRMED.value)
        medication = _make_medication(caregiver_id=caregiver_id)
        dose_repo.find_by_id.return_value = dose
        medication_repo.find_by_id.return_value = medication

        with pytest.raises(DoseAlreadyConfirmedError):
            service.confirm_dose_taken(dose_id=dose.id, caregiver_id=caregiver_id)

    def test_decrements_stock_on_confirmation(self) -> None:
        service, dose_repo, medication_repo, _ = _make_service()
        caregiver_id = uuid4()
        dose = _make_dose()
        medication = _make_medication(caregiver_id=caregiver_id, stock=10, minimum=3)
        dose_repo.find_by_id.return_value = dose
        medication_repo.find_by_id.return_value = medication

        result = service.confirm_dose_taken(dose_id=dose.id, caregiver_id=caregiver_id)

        assert medication.current_stock_units == 9
        assert dose.status == DoseStatus.CONFIRMED.value
        assert dose.taken_at is not None
        assert result.remaining_stock == 9

    def test_creates_critical_stock_alert_when_at_minimum(self) -> None:
        service, dose_repo, medication_repo, alert_repo = _make_service()
        caregiver_id = uuid4()
        dose = _make_dose()
        # stock == minimum → after decrement stock < minimum → alert
        medication = _make_medication(caregiver_id=caregiver_id, stock=4, minimum=3)
        dose_repo.find_by_id.return_value = dose
        medication_repo.find_by_id.return_value = medication

        service.confirm_dose_taken(dose_id=dose.id, caregiver_id=caregiver_id)

        # After decrement: stock=3 == minimum=3 → alert created
        alert_repo.save.assert_called_once()

    def test_stock_never_goes_below_zero(self) -> None:
        service, dose_repo, medication_repo, _ = _make_service()
        caregiver_id = uuid4()
        dose = _make_dose()
        medication = _make_medication(caregiver_id=caregiver_id, stock=0, minimum=3)
        dose_repo.find_by_id.return_value = dose
        medication_repo.find_by_id.return_value = medication

        service.confirm_dose_taken(dose_id=dose.id, caregiver_id=caregiver_id)

        assert medication.current_stock_units == 0  # stays at 0, not -1
