"""Pydantic schemas for ElderlyPatient endpoints."""

from datetime import date, datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, computed_field

from app.domain.enums import ChronicCondition


class ElderlyPatientEnrollmentRequest(BaseModel):
    """Request body for POST /patients (enroll a new patient)."""

    full_name: Annotated[str, Field(min_length=2, max_length=200)]
    date_of_birth: date
    room_number: str | None = None
    chronic_conditions: list[ChronicCondition] = []
    emergency_contact_name: str | None = None
    emergency_contact_phone: str | None = None
    notes: str | None = None


class PatientSummaryResponse(BaseModel):
    """Public summary representation of an ElderlyPatient."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    full_name: str
    date_of_birth: date
    room_number: str | None
    chronic_conditions: list[str]
    caregiver_id: UUID
    created_at: datetime

    @computed_field  # type: ignore[misc]
    @property
    def age(self) -> int:
        """Compute the patient's current age in years."""
        today = date.today()
        born = self.date_of_birth
        return today.year - born.year - ((today.month, today.day) < (born.month, born.day))
