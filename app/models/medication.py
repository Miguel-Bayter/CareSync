"""ORM model for Medication."""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Boolean, Date, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.dose import ScheduledDoseModel
    from app.models.patient import ElderlyPatientModel


class MedicationModel(TimestampMixin, Base):
    """Represents a medication prescribed to an elderly patient."""

    __tablename__ = "medications"

    patient_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("elderly_patients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    generic_name: Mapped[str] = mapped_column(String(200), nullable=False)
    brand_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    dose_mg: Mapped[float] = mapped_column(Float, nullable=False)
    frequency_hours: Mapped[int] = mapped_column(Integer, nullable=False)
    with_food: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    current_stock_units: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    minimum_stock_units: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    expiration_date: Mapped[date] = mapped_column(Date, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    patient: Mapped[ElderlyPatientModel] = relationship(
        "ElderlyPatientModel",
        back_populates="medications",
    )
    scheduled_doses: Mapped[list[ScheduledDoseModel]] = relationship(
        "ScheduledDoseModel",
        back_populates="medication",
        cascade="all, delete-orphan",
    )
