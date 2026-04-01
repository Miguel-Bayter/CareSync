"""Unit tests for MedicalReportService — PDF generation and auth checks."""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from app.core.exceptions import ForbiddenError, NotFoundError
from app.domain.enums import DoseStatus
from app.models.patient import ElderlyPatientModel
from app.services.medical_report_service import MedicalReportService


def _make_service(db: MagicMock | None = None) -> MedicalReportService:
    db = db or MagicMock()
    with (
        patch("app.services.medical_report_service.ElderlyPatientRepository"),
        patch("app.services.medical_report_service.MedicationRepository"),
        patch("app.services.medical_report_service.ScheduledDoseRepository"),
        patch("app.services.medical_report_service.AlertRepository"),
    ):
        return MedicalReportService(db=db)


def _make_patient(caregiver_id=None) -> MagicMock:
    # spec=ElderlyPatientModel ensures isinstance() check in _build_pdf passes
    patient = MagicMock(spec=ElderlyPatientModel)
    patient.id = uuid4()
    patient.caregiver_id = caregiver_id or uuid4()
    patient.full_name = "Maria Garcia"
    patient.room_number = "101"
    patient.date_of_birth = "1950-01-01"
    patient.emergency_contact_name = "Luis Garcia"
    patient.emergency_contact_phone = "+34 600 000 000"
    return patient


def _make_medication(name: str = "Aspirin") -> MagicMock:
    med = MagicMock()
    med.id = uuid4()
    med.generic_name = name
    med.dose_mg = 100.0
    return med


def _make_alert() -> MagicMock:
    alert = MagicMock()
    alert.sent_at = datetime.now(UTC)
    alert.alert_type = "dose_reminder"
    alert.message = "Please take your medication now."
    return alert


class TestGenerateMonthlyMedicalReport:
    def test_raises_not_found_when_patient_missing(self) -> None:
        service = _make_service()
        service.patient_repo.find_by_id.return_value = None

        with pytest.raises(NotFoundError):
            service.generate_monthly_medical_report(
                patient_id=uuid4(), caregiver_id=uuid4()
            )

    def test_raises_forbidden_when_wrong_caregiver(self) -> None:
        caregiver_id = uuid4()
        patient = _make_patient(caregiver_id=uuid4())  # different caregiver

        service = _make_service()
        service.patient_repo.find_by_id.return_value = patient
        service.medication_repo.find_all_by_patient.return_value = []
        service.alert_repo.find_last_month_by_patient.return_value = []

        with pytest.raises(ForbiddenError):
            service.generate_monthly_medical_report(
                patient_id=patient.id, caregiver_id=caregiver_id
            )

    def test_returns_pdf_bytes_with_no_medications_no_alerts(self) -> None:
        caregiver_id = uuid4()
        patient = _make_patient(caregiver_id=caregiver_id)

        service = _make_service()
        service.patient_repo.find_by_id.return_value = patient
        service.medication_repo.find_all_by_patient.return_value = []
        service.alert_repo.find_last_month_by_patient.return_value = []

        result = service.generate_monthly_medical_report(
            patient_id=patient.id, caregiver_id=caregiver_id
        )

        assert isinstance(result, bytes)
        assert len(result) > 0
        # PDF magic bytes
        assert result[:4] == b"%PDF"

    def test_returns_pdf_bytes_with_medications_and_alerts(self) -> None:

        caregiver_id = uuid4()
        patient = _make_patient(caregiver_id=caregiver_id)
        med = _make_medication("Metformin")
        alert = _make_alert()

        service = _make_service()
        service.patient_repo.find_by_id.return_value = patient
        service.medication_repo.find_all_by_patient.return_value = [med]
        service.alert_repo.find_last_month_by_patient.return_value = [alert]

        # Stats: 15 confirmed, 5 missed, 10 pending → 50% adherence → orange
        service.dose_repo.calculate_adherence_stats.return_value = {
            DoseStatus.CONFIRMED: 15,
            DoseStatus.MISSED: 5,
            DoseStatus.PENDING: 10,
        }

        result = service.generate_monthly_medical_report(
            patient_id=patient.id, caregiver_id=caregiver_id
        )

        assert isinstance(result, bytes)
        assert result[:4] == b"%PDF"

    def test_pdf_with_low_adherence_red_color(self) -> None:

        caregiver_id = uuid4()
        patient = _make_patient(caregiver_id=caregiver_id)
        med = _make_medication("Lisinopril")

        service = _make_service()
        service.patient_repo.find_by_id.return_value = patient
        service.medication_repo.find_all_by_patient.return_value = [med]
        service.alert_repo.find_last_month_by_patient.return_value = []

        # 2 confirmed out of 10 → 20% adherence → red
        service.dose_repo.calculate_adherence_stats.return_value = {
            DoseStatus.CONFIRMED: 2,
            DoseStatus.MISSED: 8,
            DoseStatus.PENDING: 0,
        }

        result = service.generate_monthly_medical_report(
            patient_id=patient.id, caregiver_id=caregiver_id
        )
        assert isinstance(result, bytes)


class TestAdherenceColor:
    def test_high_adherence_returns_green(self) -> None:
        color = MedicalReportService._adherence_color(80.0)
        assert color == (15, 107, 59)

    def test_medium_adherence_returns_orange(self) -> None:
        color = MedicalReportService._adherence_color(65.0)
        assert color == (180, 83, 9)

    def test_low_adherence_returns_red(self) -> None:
        color = MedicalReportService._adherence_color(30.0)
        assert color == (153, 27, 27)

    def test_boundary_80_is_green(self) -> None:
        assert MedicalReportService._adherence_color(80.0) == (15, 107, 59)

    def test_boundary_50_is_orange(self) -> None:
        assert MedicalReportService._adherence_color(50.0) == (180, 83, 9)

    def test_below_50_is_red(self) -> None:
        assert MedicalReportService._adherence_color(49.9) == (153, 27, 27)
