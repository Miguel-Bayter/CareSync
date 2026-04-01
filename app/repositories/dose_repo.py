"""Repository for ScheduledDoseModel — persistence and statistics."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.domain.enums import DoseStatus
from app.models.dose import ScheduledDoseModel
from app.repositories.base_repository import BaseRepository


class ScheduledDoseRepository(BaseRepository[ScheduledDoseModel]):
    """Data access layer for scheduled doses."""

    model_class = ScheduledDoseModel

    def __init__(self, db: Session) -> None:
        super().__init__(db)

    def bulk_schedule(self, doses: list[ScheduledDoseModel]) -> None:
        """Insert multiple doses in a single database round-trip.

        Uses db.add_all() instead of individual inserts — 1 round-trip vs N.

        Args:
            doses: List of ScheduledDoseModel instances to persist.
        """
        self.db.add_all(doses)
        self.db.flush()

    def calculate_adherence_stats(
        self, medication_id: UUID, days: int = 30
    ) -> dict[DoseStatus, int]:
        """Count doses by status for the last N days.

        Args:
            medication_id: UUID of the medication.
            days: Lookback window in days (default: 30).

        Returns:
            Dict mapping DoseStatus to count.
        """
        cutoff = datetime.now(UTC) - timedelta(days=days)
        rows = (
            self.db.query(ScheduledDoseModel.status, func.count(ScheduledDoseModel.id))
            .filter(
                ScheduledDoseModel.medication_id == medication_id,
                ScheduledDoseModel.scheduled_for >= cutoff,
            )
            .group_by(ScheduledDoseModel.status)
            .all()
        )
        stats: dict[DoseStatus, int] = {status: 0 for status in DoseStatus}
        for status_value, count in rows:
            stats[DoseStatus(status_value)] = count
        return stats
