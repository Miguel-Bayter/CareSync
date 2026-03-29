"""Business logic for elderly patient management."""

from uuid import UUID

import structlog
from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenError, PatientNotFoundError
from app.models.patient import ElderlyPatientModel
from app.repositories.patient_repo import ElderlyPatientRepository
from app.schemas.patient import ElderlyPatientEnrollmentRequest, PatientSummaryResponse

logger = structlog.get_logger(__name__)


class ElderlyPatientService:
    """Service that handles enrolling and querying elderly patients.

    Args:
        patient_repo: Repository for patient persistence.
        db: Active SQLAlchemy Session.
    """

    def __init__(self, patient_repo: ElderlyPatientRepository, db: Session) -> None:
        self._repo = patient_repo
        self._db = db

    def enroll_patient(
        self,
        request: ElderlyPatientEnrollmentRequest,
        caregiver_id: UUID,
    ) -> PatientSummaryResponse:
        """Enroll a new elderly patient under the given caregiver.

        Args:
            request: Enrollment data from the HTTP request.
            caregiver_id: UUID of the authenticated caregiver performing the action.

        Returns:
            The created PatientSummaryResponse schema.
        """
        patient = ElderlyPatientModel(
            full_name=request.full_name,
            date_of_birth=request.date_of_birth,
            room_number=request.room_number,
            caregiver_id=caregiver_id,
            chronic_conditions=[c.value for c in request.chronic_conditions],
            emergency_contact_name=request.emergency_contact_name,
            emergency_contact_phone=request.emergency_contact_phone,
            notes=request.notes,
        )
        saved = self._repo.save(patient)
        logger.info(
            "patient_enrolled",
            patient_id=str(saved.id),
            caregiver_id=str(caregiver_id),
        )
        return PatientSummaryResponse.model_validate(saved)

    def get_patient_summary(
        self,
        patient_id: UUID,
        caregiver_id: UUID,
    ) -> PatientSummaryResponse:
        """Retrieve the summary for a single patient, enforcing ownership.

        Args:
            patient_id: UUID of the target patient.
            caregiver_id: UUID of the authenticated caregiver.

        Returns:
            The PatientSummaryResponse for the patient.

        Raises:
            PatientNotFoundError: If no patient exists with the given ID.
            ForbiddenError: If the patient belongs to a different caregiver.
        """
        patient = self._repo.find_by_id(patient_id)
        if patient is None:
            raise PatientNotFoundError(str(patient_id))

        if patient.caregiver_id != caregiver_id:
            raise ForbiddenError("You do not have access to this patient.")

        return PatientSummaryResponse.model_validate(patient)

    def list_patients(self, caregiver_id: UUID) -> list[PatientSummaryResponse]:
        """Return all patients belonging to the authenticated caregiver.

        Args:
            caregiver_id: UUID of the authenticated caregiver.

        Returns:
            List of PatientSummaryResponse schemas (may be empty).
        """
        patients = self._repo.find_all_by_caregiver_id(caregiver_id)
        return [PatientSummaryResponse.model_validate(p) for p in patients]
