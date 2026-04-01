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

    def find_doses_due_in_minutes(self, minutes: int = 15) -> list[ScheduledDoseModel]:
        """Return PENDING doses scheduled within the next N minutes.

        Used by the dose reminder job to alert caregivers of upcoming doses.

        Args:
            minutes: Look-ahead window in minutes.

        Returns:
            List of ScheduledDoseModel instances due soon.
        """
        now = datetime.now(UTC)
        window_end = now + timedelta(minutes=minutes)
        return (
            self.db.query(ScheduledDoseModel)
            .filter(
                ScheduledDoseModel.status == DoseStatus.PENDING.value,
                ScheduledDoseModel.scheduled_for >= now,
                ScheduledDoseModel.scheduled_for <= window_end,
            )
            .all()
        )

    def find_overdue_doses(self, grace_minutes: int = 30) -> list[ScheduledDoseModel]:
        """Return PENDING doses that are overdue by more than grace_minutes.

        Used by the missed dose detection job.

        Args:
            grace_minutes: How many minutes past scheduled_for before marking missed.

        Returns:
            List of overdue ScheduledDoseModel instances.
        """
        cutoff = datetime.now(UTC) - timedelta(minutes=grace_minutes)
        return (
            self.db.query(ScheduledDoseModel)
            .filter(
                ScheduledDoseModel.status == DoseStatus.PENDING.value,
                ScheduledDoseModel.scheduled_for <= cutoff,
            )
            .all()
        )

    def calculate_adherence_stats(self, medication_id: UUID, days: int = 30) -> dict[DoseStatus, int]:
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
        stats: dict[DoseStatus, int] = dict.fromkeys(DoseStatus, 0)
        for status_value, count in rows:
            stats[DoseStatus(status_value)] = count
        return stats
