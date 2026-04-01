"""Medications router — enroll medications, check interactions, critical stock."""

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import CaregiverDep
from app.repositories.dose_repo import ScheduledDoseRepository
from app.repositories.medication_repo import MedicationRepository
from app.repositories.patient_repo import ElderlyPatientRepository
from app.schemas.medication import (
    CriticalStockResponse,
    DrugInteractionReport,
    MedicationEnrollmentRequest,
    MedicationResponse,
)
from app.services.drug_interaction_service import DrugInteractionService
from app.services.medication_enrollment_service import MedicationEnrollmentService

router = APIRouter(prefix="/medications", tags=["Medications"])


def _get_enrollment_service(db: Session = Depends(get_db)) -> MedicationEnrollmentService:
    return MedicationEnrollmentService(
        medication_repo=MedicationRepository(db),
        dose_repo=ScheduledDoseRepository(db),
        patient_repo=ElderlyPatientRepository(db),
        db=db,
    )


def _get_interaction_service(db: Session = Depends(get_db)) -> DrugInteractionService:
    return DrugInteractionService(medication_repo=MedicationRepository(db))


@router.post(
    "/",
    response_model=MedicationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Enroll a medication and auto-schedule 30 days of doses",
)
def enroll_medication(
    body: MedicationEnrollmentRequest,
    current_caregiver: CaregiverDep,
    service: MedicationEnrollmentService = Depends(_get_enrollment_service),
) -> MedicationResponse:
    """Register a new medication for a patient and schedule all doses for 30 days.

    Args:
        body: Medication enrollment data including patient_id and schedule.
        current_caregiver: Authenticated caregiver from JWT.
        service: Injected enrollment service.

    Returns:
        The enrolled medication with the count of doses scheduled.
    """
    return service.enroll_medication(request=body, caregiver_id=current_caregiver.id)


@router.get(
    "/{patient_id}/interactions",
    response_model=list[DrugInteractionReport],
    status_code=status.HTTP_200_OK,
    summary="Get drug interactions for all of a patient's medications",
)
def get_drug_interactions(
    patient_id: UUID,
    current_caregiver: CaregiverDep,
    service: DrugInteractionService = Depends(_get_interaction_service),
) -> list[DrugInteractionReport]:
    """Query OpenFDA for interaction data for all active medications of a patient.

    First call per drug name hits the network (~2-3s). Subsequent calls
    return instantly from the in-memory lru_cache.

    Args:
        patient_id: UUID of the patient whose medications to check.
        current_caregiver: Authenticated caregiver from JWT.
        service: Injected drug interaction service.

    Returns:
        List of DrugInteractionReport — empty if no interactions found.
    """
    return service.check_patient_drug_interactions(patient_id=patient_id)


@router.get(
    "/critical-stock",
    response_model=list[CriticalStockResponse],
    status_code=status.HTTP_200_OK,
    summary="List medications with critical stock or expiring within 7 days",
)
def get_critical_stock(
    patient_id: UUID,
    current_caregiver: CaregiverDep,
    db: Session = Depends(get_db),
) -> list[CriticalStockResponse]:
    """Return medications that need attention: low stock or expiring soon.

    Args:
        patient_id: UUID of the patient (query parameter).
        current_caregiver: Authenticated caregiver from JWT.
        db: Database session.

    Returns:
        List of CriticalStockResponse for flagged medications.
    """
    from app.core.exceptions import ForbiddenError, NotFoundError
    from app.repositories.patient_repo import ElderlyPatientRepository

    patient_repo = ElderlyPatientRepository(db)
    patient = patient_repo.find_by_id(patient_id)
    if patient is None:
        raise NotFoundError("Patient not found")
    if patient.caregiver_id != current_caregiver.id:
        raise ForbiddenError("You do not have access to this patient")

    medication_repo = MedicationRepository(db)
    medications = medication_repo.find_critical_stock(patient_id)

    today = date.today()
    return [
        CriticalStockResponse(
            medication_id=m.id,
            generic_name=m.generic_name,
            current_stock_units=m.current_stock_units,
            minimum_stock_units=m.minimum_stock_units,
            days_until_expiration=(m.expiration_date - today).days,
            is_expired=m.expiration_date < today,
        )
        for m in medications
    ]
