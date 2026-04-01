"""Repository for MedicationAlertModel — persistence operations."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy.orm import Session

from app.domain.enums import AlertType
from app.models.alert import MedicationAlertModel
from app.repositories.base_repository import BaseRepository


class AlertRepository(BaseRepository[MedicationAlertModel]):
    """Data access layer for medication alerts."""

    model_class = MedicationAlertModel

    def __init__(self, db: Session) -> None:
        super().__init__(db)

    def recent_alert_exists(
        self,
        medication_id: UUID,
        alert_type: AlertType,
        hours: int = 2,
    ) -> bool:
        """Check if an alert of the given type was recently created for a medication.

        Used for idempotency — prevents sending duplicate alerts when a job
        runs more than once within the same window.

        Args:
            medication_id: UUID of the medication.
            alert_type: Type of alert to check.
            hours: How many hours back to look.

        Returns:
            True if a recent alert exists, False otherwise.
        """
        cutoff = datetime.now(UTC) - timedelta(hours=hours)
        result = (
            self.db.query(MedicationAlertModel)
            .filter(
                MedicationAlertModel.medication_id == medication_id,
                MedicationAlertModel.alert_type == alert_type.value,
                MedicationAlertModel.sent_at >= cutoff,
            )
            .first()
        )
        return result is not None

    def find_last_month_by_patient(self, patient_id: UUID) -> list[MedicationAlertModel]:
        """Return all alerts for a patient in the last 30 days.

        Used to include alert history in the monthly medical report PDF.

        Args:
            patient_id: UUID of the patient.

        Returns:
            List of MedicationAlertModel instances ordered by sent_at desc.
        """
        cutoff = datetime.now(UTC) - timedelta(days=30)
        return (
            self.db.query(MedicationAlertModel)
            .filter(
                MedicationAlertModel.patient_id == patient_id,
                MedicationAlertModel.sent_at >= cutoff,
            )
            .order_by(MedicationAlertModel.sent_at.desc())
            .all()
        )
