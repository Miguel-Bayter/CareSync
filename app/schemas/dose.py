"""Pydantic schemas for dose tracking and adherence reporting."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class DoseConfirmRequest(BaseModel):
    """Optional notes when confirming a dose was taken."""

    notes: str | None = None


class DoseConfirmResponse(BaseModel):
    """Response after confirming a dose was taken."""

    dose_id: UUID
    medication_name: str
    taken_at: datetime
    remaining_stock: int


class AdherenceRateResponse(BaseModel):
    """Adherence statistics for a single medication."""

    medication_id: UUID
    generic_name: str
    adherence_percentage: float
    confirmed_count: int
    missed_count: int
    total_scheduled: int


class PatientAdherenceResponse(BaseModel):
    """Aggregated adherence report for all of a patient's medications."""

    patient_id: UUID
    overall_adherence: float
    medications: list[AdherenceRateResponse]
