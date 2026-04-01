"""Patients router — enroll and query elderly patients."""

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import CaregiverDep
from app.repositories.patient_repo import ElderlyPatientRepository
from app.schemas.patient import ElderlyPatientEnrollmentRequest, PatientSummaryResponse
from app.services.patient_service import ElderlyPatientService

router = APIRouter(prefix="/patients", tags=["Patients"])


def _get_patient_service(db: Session = Depends(get_db)) -> ElderlyPatientService:
    return ElderlyPatientService(patient_repo=ElderlyPatientRepository(db), db=db)


@router.post(
    "/",
    response_model=PatientSummaryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Enroll a new elderly patient",
)
def enroll_patient(
    body: ElderlyPatientEnrollmentRequest,
    current_caregiver: CaregiverDep,
    service: ElderlyPatientService = Depends(_get_patient_service),
) -> PatientSummaryResponse:
    """Enroll a new elderly patient under the authenticated caregiver.

    Args:
        body: Enrollment data.
        current_caregiver: Authenticated caregiver from JWT.
        service: Injected patient service.

    Returns:
        The newly enrolled patient's summary.
    """
    return service.enroll_patient(request=body, caregiver_id=current_caregiver.id)


@router.get(
    "/{patient_id}/summary",
    response_model=PatientSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get a patient's summary",
)
def get_patient_summary(
    patient_id: UUID,
    current_caregiver: CaregiverDep,
    service: ElderlyPatientService = Depends(_get_patient_service),
) -> PatientSummaryResponse:
    """Retrieve the summary for a specific patient.

    The caller must own the patient, otherwise 403 is returned.

    Args:
        patient_id: UUID of the target patient.
        current_caregiver: Authenticated caregiver from JWT.
        service: Injected patient service.

    Returns:
        The patient's summary.
    """
    return service.get_patient_summary(
        patient_id=patient_id,
        caregiver_id=current_caregiver.id,
    )


@router.get(
    "/",
    response_model=list[PatientSummaryResponse],
    status_code=status.HTTP_200_OK,
    summary="List all patients for the authenticated caregiver",
)
def list_patients(
    current_caregiver: CaregiverDep,
    service: ElderlyPatientService = Depends(_get_patient_service),
) -> list[PatientSummaryResponse]:
    """Return all patients belonging to the authenticated caregiver.

    Args:
        current_caregiver: Authenticated caregiver from JWT.
        service: Injected patient service.

    Returns:
        List of patient summaries.
    """
    return service.list_patients(caregiver_id=current_caregiver.id)
