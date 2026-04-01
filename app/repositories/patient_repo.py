"""Repository for ElderlyPatient persistence operations."""

from uuid import UUID

from sqlalchemy import select

from app.models.patient import ElderlyPatientModel
from app.repositories.base_repository import BaseRepository


class ElderlyPatientRepository(BaseRepository[ElderlyPatientModel]):
    """Data access layer for the elderly_patients table."""

    model_class = ElderlyPatientModel

    def find_by_id(self, id: UUID) -> ElderlyPatientModel | None:
        """Return the patient with the given UUID primary key, or None.

        Args:
            id: UUID primary key.

        Returns:
            The matching ElderlyPatientModel, or None.
        """
        return self.db.get(ElderlyPatientModel, id)

    def find_all_by_caregiver_id(self, caregiver_id: UUID) -> list[ElderlyPatientModel]:
        """Return all patients belonging to the specified caregiver.

        Args:
            caregiver_id: UUID of the responsible caregiver.

        Returns:
            List of ElderlyPatientModel instances (may be empty).
        """
        stmt = select(ElderlyPatientModel).where(ElderlyPatientModel.caregiver_id == caregiver_id)
        return list(self.db.scalars(stmt).all())
