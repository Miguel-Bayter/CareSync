"""MedicationEnrollmentService — register medications and auto-schedule doses."""

from datetime import UTC, date, datetime, timedelta
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenError, NotFoundError
from app.domain.enums import DoseStatus
from app.models.dose import ScheduledDoseModel
from app.models.medication import MedicationModel
from app.repositories.dose_repo import ScheduledDoseRepository
from app.repositories.medication_repo import MedicationRepository
from app.repositories.patient_repo import ElderlyPatientRepository
from app.schemas.medication import MedicationEnrollmentRequest, MedicationResponse


class MedicationEnrollmentService:
    """Handles medication registration and automatic dose scheduling.

    When a medication is enrolled, doses for the next 30 days are scheduled
    automatically in a single transaction.
    """

    def __init__(
        self,
        medication_repo: MedicationRepository,
        dose_repo: ScheduledDoseRepository,
        patient_repo: ElderlyPatientRepository,
        db: Session,
    ) -> None:
        self.medication_repo = medication_repo
        self.dose_repo = dose_repo
        self.patient_repo = patient_repo
        self.db = db

    def enroll_medication(
        self,
        request: MedicationEnrollmentRequest,
        caregiver_id: UUID,
    ) -> MedicationResponse:
        """Enroll a medication and auto-schedule 30 days of doses.

        Args:
            request: Medication enrollment data.
            caregiver_id: UUID of the authenticated caregiver.

        Returns:
            MedicationResponse with count of scheduled doses.

        Raises:
            NotFoundError: If the patient does not exist.
            ForbiddenError: If the patient belongs to a different caregiver.
        """
        patient = self.patient_repo.find_by_id(request.patient_id)
        if patient is None:
            raise NotFoundError("Patient not found")
        if patient.caregiver_id != caregiver_id:
            raise ForbiddenError("You do not have access to this patient")

        medication = MedicationModel(
            patient_id=request.patient_id,
            generic_name=request.generic_name,
            brand_name=request.brand_name,
            dose_mg=request.dose_mg,
            frequency_hours=request.frequency_hours,
            with_food=request.with_food,
            current_stock_units=request.current_stock_units,
            minimum_stock_units=request.minimum_stock_units,
            expiration_date=request.expiration_date,
            is_active=True,
        )
        self.medication_repo.save(medication)

        doses = self._schedule_doses(medication)
        self.dose_repo.bulk_schedule(doses)

        expiry_days = (request.expiration_date - date.today()).days
        return MedicationResponse(
            id=medication.id,
            patient_id=medication.patient_id,
            generic_name=medication.generic_name,
            brand_name=medication.brand_name,
            dose_mg=medication.dose_mg,
            frequency_hours=medication.frequency_hours,
            with_food=medication.with_food,
            current_stock_units=medication.current_stock_units,
            minimum_stock_units=medication.minimum_stock_units,
            expiration_date=medication.expiration_date,
            is_active=medication.is_active,
            is_expiring_soon=expiry_days <= 7,
            doses_scheduled=len(doses),
        )

    def _schedule_doses(self, medication: MedicationModel) -> list[ScheduledDoseModel]:
        """Build 30 days of dose objects without persisting them.

        Args:
            medication: The newly created MedicationModel (must have an id).

        Returns:
            List of ScheduledDoseModel instances ready for bulk_schedule.
        """
        total_doses = (30 * 24) // medication.frequency_hours
        now = datetime.now(UTC)
        return [
            ScheduledDoseModel(
                medication_id=medication.id,
                scheduled_for=now + timedelta(hours=i * medication.frequency_hours),
                status=DoseStatus.PENDING.value,
            )
            for i in range(total_doses)
        ]
