"""MedicationAlertService — create alerts and send email notifications via Gmail SMTP."""

import smtplib
import structlog
from datetime import UTC, datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import settings
from app.domain.enums import AlertChannel, AlertType
from app.models.alert import MedicationAlertModel
from app.models.dose import ScheduledDoseModel
from app.repositories.alert_repo import AlertRepository
from app.repositories.dose_repo import ScheduledDoseRepository
from app.repositories.medication_repo import MedicationRepository

logger = structlog.get_logger(__name__)


class MedicationAlertService:
    """Handles alert creation and email delivery for medication events.

    Email delivery is best-effort — failures are logged but never crash
    the job or the API request that triggered the alert.
    """

    def __init__(
        self,
        alert_repo: AlertRepository,
        dose_repo: ScheduledDoseRepository,
        medication_repo: MedicationRepository,
        db: Session,
    ) -> None:
        self.alert_repo = alert_repo
        self.dose_repo = dose_repo
        self.medication_repo = medication_repo
        self.db = db

    # ------------------------------------------------------------------
    # Dose reminder
    # ------------------------------------------------------------------

    def process_dose_reminders(self) -> int:
        """Find upcoming doses and send reminders. Returns count sent.

        Idempotent: skips doses that already have a reminder in the last 2 hours.
        """
        upcoming = self.dose_repo.find_doses_due_in_minutes(minutes=15)
        sent = 0
        for dose in upcoming:
            medication = self.medication_repo.find_by_id(dose.medication_id)
            if medication is None:
                continue
            if self.alert_repo.recent_alert_exists(
                medication.id, AlertType.DOSE_REMINDER, hours=2
            ):
                continue
            self._create_and_send_alert(
                patient_id=medication.patient_id,
                medication_id=medication.id,
                alert_type=AlertType.DOSE_REMINDER,
                message=(
                    f"Reminder: {medication.generic_name} "
                    f"({medication.dose_mg}mg) is due in 15 minutes."
                ),
            )
            sent += 1
        return sent

    # ------------------------------------------------------------------
    # Missed dose detection
    # ------------------------------------------------------------------

    def process_missed_doses(self) -> int:
        """Mark overdue PENDING doses as MISSED and send alerts. Returns count processed."""
        overdue = self.dose_repo.find_overdue_doses(grace_minutes=30)
        processed = 0
        for dose in overdue:
            medication = self.medication_repo.find_by_id(dose.medication_id)
            if medication is None:
                continue
            dose.status = "missed"
            if not self.alert_repo.recent_alert_exists(
                medication.id, AlertType.URGENT_MISSED_DOSE, hours=6
            ):
                self._create_and_send_alert(
                    patient_id=medication.patient_id,
                    medication_id=medication.id,
                    alert_type=AlertType.URGENT_MISSED_DOSE,
                    message=(
                        f"Missed dose: {medication.generic_name} "
                        f"({medication.dose_mg}mg) was not taken on time."
                    ),
                )
            processed += 1
        if processed:
            self.db.flush()
        return processed

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _create_and_send_alert(
        self,
        patient_id: UUID,
        medication_id: UUID,
        alert_type: AlertType,
        message: str,
    ) -> MedicationAlertModel:
        """Persist the alert record and attempt email delivery."""
        alert = MedicationAlertModel(
            patient_id=patient_id,
            medication_id=medication_id,
            alert_type=alert_type.value,
            channel=AlertChannel.EMAIL.value,
            message=message,
            sent_at=datetime.now(UTC),
            is_acknowledged=False,
        )
        self.alert_repo.save(alert)
        self._send_email_safe(subject=alert_type.value.replace("_", " ").title(), body=message)
        return alert

    def _send_email_safe(self, subject: str, body: str) -> None:
        """Send an email via Gmail SMTP. Logs errors silently — never raises."""
        gmail_user = settings.gmail_user
        gmail_password = settings.gmail_app_password.get_secret_value()

        if not gmail_user or not gmail_password:
            logger.debug("email_skipped", reason="Gmail credentials not configured")
            return

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"[CareSync] {subject}"
            msg["From"] = gmail_user
            msg["To"] = gmail_user  # Send to self — caregiver email not in scope yet
            msg.attach(MIMEText(f"<p>{body}</p>", "html"))

            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(gmail_user, gmail_password)
                server.sendmail(gmail_user, gmail_user, msg.as_string())

            logger.info("email_sent", subject=subject)
        except Exception as exc:
            logger.warning("email_failed", error=str(exc))
