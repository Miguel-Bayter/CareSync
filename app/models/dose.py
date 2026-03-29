"""ORM model for ScheduledDose."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.domain.enums import DoseStatus
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.medication import MedicationModel


class ScheduledDoseModel(TimestampMixin, Base):
    """Represents a single scheduled administration of a medication."""

    __tablename__ = "scheduled_doses"

    medication_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("medications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    scheduled_for: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=DoseStatus.PENDING.value,
    )
    taken_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Relationships
    medication: Mapped[MedicationModel] = relationship(
        "MedicationModel",
        back_populates="scheduled_doses",
    )
