"""ORM model for ElderlyPatient."""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Date, ForeignKey, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.caregiver import ResponsibleCaregiverModel
    from app.models.medication import MedicationModel


class ElderlyPatientModel(TimestampMixin, Base):
    """Represents an elderly patient whose medication is managed by a caregiver."""

    __tablename__ = "elderly_patients"

    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    date_of_birth: Mapped[date] = mapped_column(Date, nullable=False)
    room_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    caregiver_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("responsible_caregivers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Stored as a JSON array of strings; values come from ChronicCondition enum.
    # JSON is supported by both PostgreSQL (production) and SQLite (tests).
    chronic_conditions: Mapped[list[str]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
        server_default="[]",
    )
    emergency_contact_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    emergency_contact_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    caregiver: Mapped[ResponsibleCaregiverModel] = relationship(
        "ResponsibleCaregiverModel",
        back_populates="patients",
    )
    medications: Mapped[list[MedicationModel]] = relationship(
        "MedicationModel",
        back_populates="patient",
        cascade="all, delete-orphan",
    )
