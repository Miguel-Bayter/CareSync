"""Pydantic schemas for medication enrollment and responses."""

from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class MedicationEnrollmentRequest(BaseModel):
    """Request body for enrolling a new medication for a patient."""

    patient_id: UUID
    generic_name: str = Field(min_length=1, max_length=200)
    brand_name: str | None = Field(default=None, max_length=200)
    dose_mg: float = Field(gt=0, description="Dose in milligrams")
    frequency_hours: int = Field(ge=1, le=24, description="Hours between doses")
    with_food: bool = Field(description="Whether the medication must be taken with food")
    current_stock_units: int = Field(ge=0, description="Current units in stock")
    minimum_stock_units: int = Field(ge=1, description="Threshold for critical stock alert")
    expiration_date: date

    @model_validator(mode="after")
    def validate_expiration_not_in_past(self) -> "MedicationEnrollmentRequest":
        if self.expiration_date < date.today():
            raise ValueError("Expiration date cannot be in the past")
        return self


class MedicationResponse(BaseModel):
    """Response schema for a medication, including computed fields."""

    id: UUID
    patient_id: UUID
    generic_name: str
    brand_name: str | None
    dose_mg: float
    frequency_hours: int
    with_food: bool
    current_stock_units: int
    minimum_stock_units: int
    expiration_date: date
    is_active: bool
    is_expiring_soon: bool
    doses_scheduled: int

    model_config = ConfigDict(from_attributes=True)


class DrugInteractionReport(BaseModel):
    """Report of a potential drug interaction from OpenFDA."""

    medication_name: str
    interaction_text: str


class CriticalStockResponse(BaseModel):
    """Response for a medication with critical stock or near expiration."""

    medication_id: UUID
    generic_name: str
    current_stock_units: int
    minimum_stock_units: int
    days_until_expiration: int
    is_expired: bool
