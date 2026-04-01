"""Background jobs executed by APScheduler.

Each job owns its own database session — never shared with API requests.
All jobs are idempotent: safe to run multiple times without side effects.
"""

import structlog

from app.database import SessionLocal
from app.repositories.alert_repo import AlertRepository
from app.repositories.dose_repo import ScheduledDoseRepository
from app.repositories.medication_repo import MedicationRepository
from app.repositories.patient_repo import ElderlyPatientRepository
from app.services.alert_service import MedicationAlertService

logger = structlog.get_logger(__name__)


def dose_reminder_job() -> None:
    """Run every minute — send reminders for doses due in the next 15 minutes.

    Idempotent: skips medications that already have a reminder sent in the
    last 2 hours so caregivers never receive duplicate notifications.
    """
    db = SessionLocal()
    try:
        service = MedicationAlertService(
            alert_repo=AlertRepository(db),
            dose_repo=ScheduledDoseRepository(db),
            medication_repo=MedicationRepository(db),
            db=db,
        )
        sent = service.process_dose_reminders()
        db.commit()
        logger.info("dose_reminder_job_complete", reminders_sent=sent)
    except Exception as exc:
        db.rollback()
        logger.error("dose_reminder_job_failed", error=str(exc))
    finally:
        db.close()


def missed_dose_detection_job() -> None:
    """Run every 5 minutes — mark overdue doses as MISSED and alert caregivers.

    A dose is considered missed if it is still PENDING 30+ minutes after its
    scheduled time. Idempotent: duplicate alerts are suppressed by a 6-hour
    cooldown per medication.
    """
    db = SessionLocal()
    try:
        service = MedicationAlertService(
            alert_repo=AlertRepository(db),
            dose_repo=ScheduledDoseRepository(db),
            medication_repo=MedicationRepository(db),
            db=db,
        )
        count = service.process_missed_doses()
        db.commit()
        logger.info("missed_dose_job_complete", missed_processed=count)
    except Exception as exc:
        db.rollback()
        logger.error("missed_dose_job_failed", error=str(exc))
    finally:
        db.close()


def daily_stock_check_job() -> None:
    """Run every day at 8 AM — log critical stock levels for all patients.

    Iterates all active patients and logs any medications below minimum stock
    or expiring within 7 days. Email alerts for critical stock are already
    triggered at dose confirmation time (DoseTrackingService); this job
    provides a daily summary in the logs.
    """
    db = SessionLocal()
    try:
        ElderlyPatientRepository(db)
        medication_repo = MedicationRepository(db)

        # Gather all caregivers' patients via a direct query
        from app.models.patient import ElderlyPatientModel

        patients = db.query(ElderlyPatientModel).all()

        critical_total = 0
        for patient in patients:
            critical = medication_repo.find_critical_stock(patient.id)
            if critical:
                critical_total += len(critical)
                for med in critical:
                    logger.warning(
                        "daily_stock_critical",
                        patient=patient.full_name,
                        medication=med.generic_name,
                        stock=med.current_stock_units,
                        minimum=med.minimum_stock_units,
                    )

        logger.info("daily_stock_job_complete", critical_medications=critical_total)
    except Exception as exc:
        logger.error("daily_stock_job_failed", error=str(exc))
    finally:
        db.close()
