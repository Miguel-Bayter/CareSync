"""Integration tests for repository query methods using in-memory SQLite."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.domain.enums import AlertChannel, AlertType, DoseStatus
from app.models.alert import MedicationAlertModel
from app.models.dose import ScheduledDoseModel
from app.repositories.alert_repo import AlertRepository
from app.repositories.dose_repo import ScheduledDoseRepository
from tests.factories.caregiver_factory import CaregiverFactory
from tests.factories.medication_factory import MedicationFactory
from tests.factories.patient_factory import PatientFactory

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _create_caregiver(db):
    CaregiverFactory._meta.sqlalchemy_session = db
    return CaregiverFactory()


def _create_patient(db, caregiver=None):
    CaregiverFactory._meta.sqlalchemy_session = db
    PatientFactory._meta.sqlalchemy_session = db
    if caregiver:
        return PatientFactory(caregiver=caregiver, caregiver_id=caregiver.id)
    return PatientFactory()


def _create_medication(db, patient):
    MedicationFactory._meta.sqlalchemy_session = db
    return MedicationFactory(patient_id=patient.id)


def _create_dose(db, medication_id, status=DoseStatus.PENDING.value, minutes_offset=5):
    dose = ScheduledDoseModel(
        medication_id=medication_id,
        scheduled_for=datetime.now(UTC) + timedelta(minutes=minutes_offset),
        status=status,
    )
    db.add(dose)
    db.flush()
    return dose


def _create_alert(db, patient_id, medication_id=None, alert_type=AlertType.DOSE_REMINDER, hours_ago=0):
    alert = MedicationAlertModel(
        patient_id=patient_id,
        medication_id=medication_id or uuid4(),
        alert_type=alert_type.value,
        channel=AlertChannel.EMAIL.value,
        message="Test alert",
        sent_at=datetime.now(UTC) - timedelta(hours=hours_ago),
        is_acknowledged=False,
    )
    db.add(alert)
    db.flush()
    return alert


# ---------------------------------------------------------------------------
# BaseRepository.delete
# ---------------------------------------------------------------------------


class TestBaseRepositoryDelete:
    def test_delete_removes_entity(self, db_session) -> None:
        caregiver = _create_caregiver(db_session)
        patient = _create_patient(db_session, caregiver=caregiver)
        med = _create_medication(db_session, patient)
        dose = _create_dose(db_session, med.id)

        repo = ScheduledDoseRepository(db_session)
        repo.delete(dose)

        assert repo.find_by_id(dose.id) is None


# ---------------------------------------------------------------------------
# AlertRepository
# ---------------------------------------------------------------------------


class TestAlertRepository:
    def test_recent_alert_exists_returns_true_when_within_window(self, db_session) -> None:
        caregiver = _create_caregiver(db_session)
        patient = _create_patient(db_session, caregiver=caregiver)
        med = _create_medication(db_session, patient)
        _create_alert(db_session, patient.id, med.id, AlertType.DOSE_REMINDER, hours_ago=1)

        repo = AlertRepository(db_session)
        result = repo.recent_alert_exists(med.id, AlertType.DOSE_REMINDER, hours=2)

        assert result is True

    def test_recent_alert_exists_returns_false_when_outside_window(self, db_session) -> None:
        caregiver = _create_caregiver(db_session)
        patient = _create_patient(db_session, caregiver=caregiver)
        med = _create_medication(db_session, patient)
        _create_alert(db_session, patient.id, med.id, AlertType.DOSE_REMINDER, hours_ago=5)

        repo = AlertRepository(db_session)
        result = repo.recent_alert_exists(med.id, AlertType.DOSE_REMINDER, hours=2)

        assert result is False

    def test_recent_alert_exists_returns_false_when_no_alerts(self, db_session) -> None:
        repo = AlertRepository(db_session)
        result = repo.recent_alert_exists(uuid4(), AlertType.DOSE_REMINDER)

        assert result is False

    def test_find_last_month_by_patient_returns_recent_alerts(self, db_session) -> None:
        caregiver = _create_caregiver(db_session)
        patient = _create_patient(db_session, caregiver=caregiver)
        med = _create_medication(db_session, patient)
        alert1 = _create_alert(db_session, patient.id, med.id, hours_ago=1)
        alert2 = _create_alert(db_session, patient.id, med.id, hours_ago=5)

        repo = AlertRepository(db_session)
        results = repo.find_last_month_by_patient(patient.id)

        ids = [r.id for r in results]
        assert alert1.id in ids
        assert alert2.id in ids

    def test_find_last_month_by_patient_excludes_old_alerts(self, db_session) -> None:
        caregiver = _create_caregiver(db_session)
        patient = _create_patient(db_session, caregiver=caregiver)
        med = _create_medication(db_session, patient)
        # Alert from 35 days ago — outside the 30-day window
        old_alert = MedicationAlertModel(
            patient_id=patient.id,
            medication_id=med.id,
            alert_type=AlertType.DOSE_REMINDER.value,
            channel=AlertChannel.EMAIL.value,
            message="Old alert",
            sent_at=datetime.now(UTC) - timedelta(days=35),
            is_acknowledged=False,
        )
        db_session.add(old_alert)
        db_session.flush()

        repo = AlertRepository(db_session)
        results = repo.find_last_month_by_patient(patient.id)

        assert old_alert.id not in [r.id for r in results]

    def test_find_last_month_returns_ordered_by_sent_at_desc(self, db_session) -> None:
        caregiver = _create_caregiver(db_session)
        patient = _create_patient(db_session, caregiver=caregiver)
        med = _create_medication(db_session, patient)
        _create_alert(db_session, patient.id, med.id, hours_ago=10)
        newer = _create_alert(db_session, patient.id, med.id, hours_ago=1)

        repo = AlertRepository(db_session)
        results = repo.find_last_month_by_patient(patient.id)

        # First result should be the most recent
        assert results[0].id == newer.id


# ---------------------------------------------------------------------------
# ScheduledDoseRepository query methods
# ---------------------------------------------------------------------------


class TestScheduledDoseRepository:
    def test_find_doses_due_in_minutes_returns_upcoming_pending(self, db_session) -> None:
        caregiver = _create_caregiver(db_session)
        patient = _create_patient(db_session, caregiver=caregiver)
        med = _create_medication(db_session, patient)
        due_soon = _create_dose(db_session, med.id, minutes_offset=10)

        repo = ScheduledDoseRepository(db_session)
        results = repo.find_doses_due_in_minutes(minutes=15)

        assert any(d.id == due_soon.id for d in results)

    def test_find_doses_due_in_minutes_excludes_past_doses(self, db_session) -> None:
        caregiver = _create_caregiver(db_session)
        patient = _create_patient(db_session, caregiver=caregiver)
        med = _create_medication(db_session, patient)
        past_dose = _create_dose(db_session, med.id, minutes_offset=-60)

        repo = ScheduledDoseRepository(db_session)
        results = repo.find_doses_due_in_minutes(minutes=15)

        assert all(d.id != past_dose.id for d in results)

    def test_find_doses_due_in_minutes_excludes_already_confirmed(self, db_session) -> None:
        caregiver = _create_caregiver(db_session)
        patient = _create_patient(db_session, caregiver=caregiver)
        med = _create_medication(db_session, patient)
        confirmed = _create_dose(db_session, med.id, status=DoseStatus.CONFIRMED.value, minutes_offset=5)

        repo = ScheduledDoseRepository(db_session)
        results = repo.find_doses_due_in_minutes(minutes=15)

        assert all(d.id != confirmed.id for d in results)

    def test_find_overdue_doses_returns_late_pending(self, db_session) -> None:
        caregiver = _create_caregiver(db_session)
        patient = _create_patient(db_session, caregiver=caregiver)
        med = _create_medication(db_session, patient)
        overdue = _create_dose(db_session, med.id, minutes_offset=-60)

        repo = ScheduledDoseRepository(db_session)
        results = repo.find_overdue_doses(grace_minutes=30)

        assert any(d.id == overdue.id for d in results)

    def test_find_overdue_doses_excludes_within_grace_period(self, db_session) -> None:
        caregiver = _create_caregiver(db_session)
        patient = _create_patient(db_session, caregiver=caregiver)
        med = _create_medication(db_session, patient)
        grace_dose = _create_dose(db_session, med.id, minutes_offset=-10)  # only 10min late

        repo = ScheduledDoseRepository(db_session)
        results = repo.find_overdue_doses(grace_minutes=30)

        assert all(d.id != grace_dose.id for d in results)
