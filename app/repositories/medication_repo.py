"""Repository for MedicationModel — persistence operations."""

from datetime import date, timedelta
from uuid import UUID

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.medication import MedicationModel
from app.repositories.base_repository import BaseRepository


class MedicationRepository(BaseRepository[MedicationModel]):
    """Data access layer for medications."""

    model_class = MedicationModel

    def __init__(self, db: Session) -> None:
        super().__init__(db)

    def find_all_by_patient(self, patient_id: UUID) -> list[MedicationModel]:
        """Return all active medications for a given patient.

        Args:
            patient_id: UUID of the patient.

        Returns:
            List of active MedicationModel instances.
        """
        return (
            self.db.query(MedicationModel)
            .filter(
                MedicationModel.patient_id == patient_id,
                MedicationModel.is_active == True,  # noqa: E712
            )
            .all()
        )

    def find_critical_stock(self, patient_id: UUID) -> list[MedicationModel]:
        """Return medications that are low on stock or expiring within 7 days.

        Args:
            patient_id: UUID of the patient.

        Returns:
            List of MedicationModel instances flagged as critical.
        """
        expiry_threshold = date.today() + timedelta(days=7)
        return (
            self.db.query(MedicationModel)
            .filter(
                MedicationModel.patient_id == patient_id,
                MedicationModel.is_active == True,  # noqa: E712
                or_(
                    MedicationModel.current_stock_units <= MedicationModel.minimum_stock_units,
                    MedicationModel.expiration_date <= expiry_threshold,
                ),
            )
            .all()
        )
