"""Unit tests for scheduler/jobs.py — mocked DB and service layer."""

from unittest.mock import MagicMock, patch

from app.scheduler.jobs import (
    daily_stock_check_job,
    dose_reminder_job,
    missed_dose_detection_job,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_session() -> MagicMock:
    """Return a mock that behaves like a SQLAlchemy Session."""
    session = MagicMock()
    session.__enter__ = MagicMock(return_value=session)
    session.__exit__ = MagicMock(return_value=False)
    return session


# ---------------------------------------------------------------------------
# dose_reminder_job
# ---------------------------------------------------------------------------


class TestDoseReminderJob:
    @patch("app.scheduler.jobs.MedicationAlertService")
    @patch("app.scheduler.jobs.SessionLocal")
    def test_calls_process_dose_reminders(self, mock_session_local: MagicMock, mock_service_cls: MagicMock) -> None:
        db = _make_session()
        mock_session_local.return_value = db
        mock_service = MagicMock()
        mock_service.process_dose_reminders.return_value = 3
        mock_service_cls.return_value = mock_service

        dose_reminder_job()

        mock_service.process_dose_reminders.assert_called_once()

    @patch("app.scheduler.jobs.MedicationAlertService")
    @patch("app.scheduler.jobs.SessionLocal")
    def test_commits_on_success(self, mock_session_local: MagicMock, mock_service_cls: MagicMock) -> None:
        db = _make_session()
        mock_session_local.return_value = db
        mock_service = MagicMock()
        mock_service.process_dose_reminders.return_value = 1
        mock_service_cls.return_value = mock_service

        dose_reminder_job()

        db.commit.assert_called_once()
        db.rollback.assert_not_called()

    @patch("app.scheduler.jobs.MedicationAlertService")
    @patch("app.scheduler.jobs.SessionLocal")
    def test_rollback_on_exception(self, mock_session_local: MagicMock, mock_service_cls: MagicMock) -> None:
        db = _make_session()
        mock_session_local.return_value = db
        mock_service = MagicMock()
        mock_service.process_dose_reminders.side_effect = RuntimeError("DB error")
        mock_service_cls.return_value = mock_service

        # Should NOT raise — jobs are fire-and-forget
        dose_reminder_job()

        db.rollback.assert_called_once()
        db.commit.assert_not_called()

    @patch("app.scheduler.jobs.MedicationAlertService")
    @patch("app.scheduler.jobs.SessionLocal")
    def test_always_closes_session(self, mock_session_local: MagicMock, mock_service_cls: MagicMock) -> None:
        db = _make_session()
        mock_session_local.return_value = db
        mock_service = MagicMock()
        mock_service.process_dose_reminders.side_effect = RuntimeError("fail")
        mock_service_cls.return_value = mock_service

        dose_reminder_job()

        db.close.assert_called_once()


# ---------------------------------------------------------------------------
# missed_dose_detection_job
# ---------------------------------------------------------------------------


class TestMissedDoseDetectionJob:
    @patch("app.scheduler.jobs.MedicationAlertService")
    @patch("app.scheduler.jobs.SessionLocal")
    def test_calls_process_missed_doses(self, mock_session_local: MagicMock, mock_service_cls: MagicMock) -> None:
        db = _make_session()
        mock_session_local.return_value = db
        mock_service = MagicMock()
        mock_service.process_missed_doses.return_value = 2
        mock_service_cls.return_value = mock_service

        missed_dose_detection_job()

        mock_service.process_missed_doses.assert_called_once()

    @patch("app.scheduler.jobs.MedicationAlertService")
    @patch("app.scheduler.jobs.SessionLocal")
    def test_commits_on_success(self, mock_session_local: MagicMock, mock_service_cls: MagicMock) -> None:
        db = _make_session()
        mock_session_local.return_value = db
        mock_service = MagicMock()
        mock_service.process_missed_doses.return_value = 0
        mock_service_cls.return_value = mock_service

        missed_dose_detection_job()

        db.commit.assert_called_once()

    @patch("app.scheduler.jobs.MedicationAlertService")
    @patch("app.scheduler.jobs.SessionLocal")
    def test_rollback_on_exception(self, mock_session_local: MagicMock, mock_service_cls: MagicMock) -> None:
        db = _make_session()
        mock_session_local.return_value = db
        mock_service = MagicMock()
        mock_service.process_missed_doses.side_effect = Exception("fail")
        mock_service_cls.return_value = mock_service

        missed_dose_detection_job()

        db.rollback.assert_called_once()

    @patch("app.scheduler.jobs.MedicationAlertService")
    @patch("app.scheduler.jobs.SessionLocal")
    def test_always_closes_session(self, mock_session_local: MagicMock, mock_service_cls: MagicMock) -> None:
        db = _make_session()
        mock_session_local.return_value = db
        mock_service = MagicMock()
        mock_service.process_missed_doses.side_effect = Exception("fail")
        mock_service_cls.return_value = mock_service

        missed_dose_detection_job()

        db.close.assert_called_once()


# ---------------------------------------------------------------------------
# daily_stock_check_job
# ---------------------------------------------------------------------------


class TestDailyStockCheckJob:
    @patch("app.scheduler.jobs.SessionLocal")
    def test_no_patients_logs_zero_critical(self, mock_session_local: MagicMock) -> None:
        db = _make_session()
        db.query.return_value.all.return_value = []
        mock_session_local.return_value = db

        # Should complete without error even with no patients
        daily_stock_check_job()

        db.close.assert_called_once()

    @patch("app.scheduler.jobs.MedicationRepository")
    @patch("app.scheduler.jobs.SessionLocal")
    def test_iterates_patients_and_checks_stock(
        self, mock_session_local: MagicMock, mock_med_repo_cls: MagicMock
    ) -> None:
        db = _make_session()

        patient = MagicMock()
        patient.id = "patient-uuid-1"
        patient.full_name = "Maria Garcia"

        db.query.return_value.all.return_value = [patient]

        med_repo = MagicMock()
        low_stock_med = MagicMock()
        low_stock_med.generic_name = "Aspirin"
        low_stock_med.current_stock_units = 2
        low_stock_med.minimum_stock_units = 10
        med_repo.find_critical_stock.return_value = [low_stock_med]
        mock_med_repo_cls.return_value = med_repo

        mock_session_local.return_value = db

        daily_stock_check_job()

        med_repo.find_critical_stock.assert_called_once_with("patient-uuid-1")
        db.close.assert_called_once()

    @patch("app.scheduler.jobs.SessionLocal")
    def test_handles_exception_without_raising(self, mock_session_local: MagicMock) -> None:
        db = _make_session()
        db.query.side_effect = RuntimeError("DB exploded")
        mock_session_local.return_value = db

        # Job must not raise — errors are logged and swallowed
        daily_stock_check_job()

        db.close.assert_called_once()

    @patch("app.scheduler.jobs.MedicationRepository")
    @patch("app.scheduler.jobs.SessionLocal")
    def test_multiple_patients_are_all_checked(
        self, mock_session_local: MagicMock, mock_med_repo_cls: MagicMock
    ) -> None:
        db = _make_session()

        patients = [MagicMock(id=f"p-{i}", full_name=f"Patient {i}") for i in range(3)]
        db.query.return_value.all.return_value = patients

        med_repo = MagicMock()
        med_repo.find_critical_stock.return_value = []
        mock_med_repo_cls.return_value = med_repo

        mock_session_local.return_value = db

        daily_stock_check_job()

        assert med_repo.find_critical_stock.call_count == 3
