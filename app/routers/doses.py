"""Doses router — confirm dose taken, get adherence report."""

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import CaregiverDep
from app.repositories.alert_repo import AlertRepository
from app.repositories.dose_repo import ScheduledDoseRepository
from app.repositories.medication_repo import MedicationRepository
from app.schemas.dose import DoseConfirmRequest, DoseConfirmResponse, PatientAdherenceResponse
from app.services.dose_tracking_service import DoseTrackingService

router = APIRouter(prefix="/doses", tags=["Doses"])


def _get_tracking_service(db: Session = Depends(get_db)) -> DoseTrackingService:
    return DoseTrackingService(
        dose_repo=ScheduledDoseRepository(db),
        medication_repo=MedicationRepository(db),
        alert_repo=AlertRepository(db),
        db=db,
    )


@router.post(
    "/{dose_id}/confirm",
    response_model=DoseConfirmResponse,
    status_code=status.HTTP_200_OK,
    summary="Confirm a scheduled dose was taken",
)
def confirm_dose(
    dose_id: UUID,
    body: DoseConfirmRequest,
    current_caregiver: CaregiverDep,
    service: DoseTrackingService = Depends(_get_tracking_service),
) -> DoseConfirmResponse:
    """Mark a dose as taken, decrement medication stock, and trigger alert if critical.

    Args:
        dose_id: UUID of the ScheduledDose to confirm.
        body: Optional notes.
        current_caregiver: Authenticated caregiver from JWT.
        service: Injected dose tracking service.

    Returns:
        Confirmation details including remaining stock.
    """
    return service.confirm_dose_taken(
        dose_id=dose_id,
        caregiver_id=current_caregiver.id,
        notes=body.notes,
    )


@router.get(
    "/adherence/{patient_id}",
    response_model=PatientAdherenceResponse,
    status_code=status.HTTP_200_OK,
    summary="Get medication adherence report for a patient",
)
def get_adherence_report(
    patient_id: UUID,
    current_caregiver: CaregiverDep,
    service: DoseTrackingService = Depends(_get_tracking_service),
) -> PatientAdherenceResponse:
    """Calculate adherence percentage for each of a patient's medications (last 30 days).

    Args:
        patient_id: UUID of the patient.
        current_caregiver: Authenticated caregiver from JWT.
        service: Injected dose tracking service.

    Returns:
        Per-medication adherence rates and overall patient adherence.
    """
    return service.get_patient_adherence(
        patient_id=patient_id,
        caregiver_id=current_caregiver.id,
    )
