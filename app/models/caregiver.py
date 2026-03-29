"""ORM model for ResponsibleCaregiver."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.patient import ElderlyPatientModel


class ResponsibleCaregiverModel(TimestampMixin, Base):
    """Represents a responsible caregiver who manages one or more elderly patients."""

    __tablename__ = "responsible_caregivers"

    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(200), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    patients: Mapped[list[ElderlyPatientModel]] = relationship(
        "ElderlyPatientModel",
        back_populates="caregiver",
        cascade="all, delete-orphan",
    )
