"""Unit tests for MedicationAlertService."""

import smtplib
from unittest.mock import MagicMock, patch
from uuid import uuid4

from app.domain.enums import AlertType
from app.services.alert_service import MedicationAlertService


def _make_service():
    alert_repo = MagicMock()
    dose_repo = MagicMock()
    medication_repo = MagicMock()
    db = MagicMock()
    service = MedicationAlertService(
        alert_repo=alert_repo,
        dose_repo=dose_repo,
        medication_repo=medication_repo,
        db=db,
    )
    return service, alert_repo, dose_repo, medication_repo


def _make_dose() -> MagicMock:
    dose = MagicMock()
    dose.id = uuid4()
    dose.medication_id = uuid4()
    return dose


def _make_medication() -> MagicMock:
    med = MagicMock()
    med.id = uuid4()
    med.patient_id = uuid4()
    med.generic_name = "metformin"
    med.dose_mg = 850.0
    return med


class TestProcessDoseReminders:
    def test_returns_zero_when_no_upcoming_doses(self) -> None:
        service, _, dose_repo, _ = _make_service()
        dose_repo.find_doses_due_in_minutes.return_value = []

        assert service.process_dose_reminders() == 0

    def test_skips_when_recent_reminder_already_sent(self) -> None:
        service, alert_repo, dose_repo, medication_repo = _make_service()
        dose = _make_dose()
        dose_repo.find_doses_due_in_minutes.return_value = [dose]
        medication_repo.find_by_id.return_value = _make_medication()
        alert_repo.recent_alert_exists.return_value = True

        result = service.process_dose_reminders()

        assert result == 0
        alert_repo.save.assert_not_called()

    def test_creates_alert_when_no_recent_reminder(self) -> None:
        service, alert_repo, dose_repo, medication_repo = _make_service()
        dose = _make_dose()
        dose_repo.find_doses_due_in_minutes.return_value = [dose]
        medication_repo.find_by_id.return_value = _make_medication()
        alert_repo.recent_alert_exists.return_value = False

        with patch.object(service, "_send_email_safe"):
            result = service.process_dose_reminders()

        assert result == 1
        alert_repo.save.assert_called_once()

    def test_skips_dose_when_medication_not_found(self) -> None:
        service, alert_repo, dose_repo, medication_repo = _make_service()
        dose_repo.find_doses_due_in_minutes.return_value = [_make_dose()]
        medication_repo.find_by_id.return_value = None

        result = service.process_dose_reminders()

        assert result == 0
        alert_repo.save.assert_not_called()

    def test_counts_multiple_reminders_correctly(self) -> None:
        service, alert_repo, dose_repo, medication_repo = _make_service()
        doses = [_make_dose(), _make_dose(), _make_dose()]
        dose_repo.find_doses_due_in_minutes.return_value = doses
        medication_repo.find_by_id.return_value = _make_medication()
        alert_repo.recent_alert_exists.return_value = False

        with patch.object(service, "_send_email_safe"):
            result = service.process_dose_reminders()

        assert result == 3
        assert alert_repo.save.call_count == 3


class TestProcessMissedDoses:
    def test_returns_zero_when_no_overdue_doses(self) -> None:
        service, _, dose_repo, _ = _make_service()
        dose_repo.find_overdue_doses.return_value = []

        assert service.process_missed_doses() == 0

    def test_marks_overdue_dose_as_missed(self) -> None:
        service, alert_repo, dose_repo, medication_repo = _make_service()
        dose = _make_dose()
        dose.status = "pending"
        dose_repo.find_overdue_doses.return_value = [dose]
        medication_repo.find_by_id.return_value = _make_medication()
        alert_repo.recent_alert_exists.return_value = False

        with patch.object(service, "_send_email_safe"):
            result = service.process_missed_doses()

        assert result == 1
        assert dose.status == "missed"

    def test_does_not_create_duplicate_alert_when_recent_exists(self) -> None:
        service, alert_repo, dose_repo, medication_repo = _make_service()
        dose = _make_dose()
        dose_repo.find_overdue_doses.return_value = [dose]
        medication_repo.find_by_id.return_value = _make_medication()
        alert_repo.recent_alert_exists.return_value = True

        result = service.process_missed_doses()

        assert result == 1  # still counted as processed
        alert_repo.save.assert_not_called()

    def test_skips_missed_dose_when_medication_not_found(self) -> None:
        service, alert_repo, dose_repo, medication_repo = _make_service()
        dose_repo.find_overdue_doses.return_value = [_make_dose()]
        medication_repo.find_by_id.return_value = None

        result = service.process_missed_doses()

        assert result == 0

    def test_flushes_db_when_doses_processed(self) -> None:
        service, alert_repo, dose_repo, medication_repo = _make_service()
        dose = _make_dose()
        dose_repo.find_overdue_doses.return_value = [dose]
        medication_repo.find_by_id.return_value = _make_medication()
        alert_repo.recent_alert_exists.return_value = False

        with patch.object(service, "_send_email_safe"):
            service.process_missed_doses()

        service.db.flush.assert_called_once()


class TestSendEmailSafe:
    def test_skips_when_gmail_user_not_configured(self) -> None:
        service, _, _, _ = _make_service()
        with patch("app.services.alert_service.settings") as mock_settings:
            mock_settings.gmail_user = ""
            mock_settings.gmail_app_password.get_secret_value.return_value = ""
            # Must not raise
            service._send_email_safe(subject="Test", body="Test body")

    def test_handles_smtp_error_without_raising(self) -> None:
        service, _, _, _ = _make_service()
        with patch("app.services.alert_service.settings") as mock_settings:
            mock_settings.gmail_user = "test@gmail.com"
            mock_settings.gmail_app_password.get_secret_value.return_value = "apppassword"
            with patch("smtplib.SMTP_SSL", side_effect=smtplib.SMTPException("Connection refused")):
                # Must not raise
                service._send_email_safe(subject="Reminder", body="Take your medication.")

    def test_sends_email_successfully_via_smtp(self) -> None:
        service, _, _, _ = _make_service()
        with patch("app.services.alert_service.settings") as mock_settings:
            mock_settings.gmail_user = "test@gmail.com"
            mock_settings.gmail_app_password.get_secret_value.return_value = "apppassword"
            mock_server = MagicMock()
            with patch("smtplib.SMTP_SSL") as mock_smtp_cls:
                mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=mock_server)
                mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)
                service._send_email_safe(subject="Reminder", body="Take your medication.")
            mock_server.login.assert_called_once_with("test@gmail.com", "apppassword")
            mock_server.sendmail.assert_called_once()
