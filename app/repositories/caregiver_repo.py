"""Repository for ResponsibleCaregiver persistence operations."""

from uuid import UUID

from sqlalchemy import select

from app.models.caregiver import ResponsibleCaregiverModel
from app.repositories.base_repository import BaseRepository


class CaregiverRepository(BaseRepository[ResponsibleCaregiverModel]):
    """Data access layer for the responsible_caregivers table."""

    model_class = ResponsibleCaregiverModel

    def find_by_email(self, email: str) -> ResponsibleCaregiverModel | None:
        """Return the caregiver with the given e-mail address, or None.

        Args:
            email: The e-mail address to search for (case-sensitive match).

        Returns:
            The matching ResponsibleCaregiverModel, or None.
        """
        stmt = select(ResponsibleCaregiverModel).where(
            ResponsibleCaregiverModel.email == email
        )
        return self.db.scalar(stmt)

    def find_by_id(self, id: UUID) -> ResponsibleCaregiverModel | None:
        """Return the caregiver with the given UUID primary key, or None.

        Args:
            id: UUID primary key.

        Returns:
            The matching ResponsibleCaregiverModel, or None.
        """
        return self.db.get(ResponsibleCaregiverModel, id)
