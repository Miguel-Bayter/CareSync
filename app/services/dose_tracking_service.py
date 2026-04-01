"""DoseTrackingService — confirm doses, decrement stock, calculate adherence."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import (
    DoseAlreadyConfirmedError,
    DoseNotFoundError,
    ForbiddenError,
    MedicationNotFoundError,
)
from app.domain.enums import AlertChannel, AlertType, DoseStatus
from app.models.alert import MedicationAlertModel
from app.repositories.alert_repo import AlertRepository
from app.repositories.dose_repo import ScheduledDoseRepository
from app.repositories.medication_repo import MedicationRepository
from app.schemas.dose import (
    AdherenceRateResponse,
    DoseConfirmResponse,
    PatientAdherenceResponse,
)


class DoseTrackingService:
    """Handles dose confirmation with stock decrement and adherence reporting.

    All operations that modify state (confirm, stock decrement, alert creation)
    run within the same unit of work — if any step fails, the entire operation
    rolls back.
    """

    def __init__(
        self,
        dose_repo: ScheduledDoseRepository,
        medication_repo: MedicationRepository,
        alert_repo: AlertRepository,
        db: Session,
    ) -> None:
        self.dose_repo = dose_repo
        self.medication_repo = medication_repo
        self.alert_repo = alert_repo
        self.db = db

    def confirm_dose_taken(
        self,
        dose_id: UUID,
        caregiver_id: UUID,
        notes: str | None = None,
    ) -> DoseConfirmResponse:
        """Mark a dose as taken, decrement stock, and create alert if stock is critical.

        Args:
            dose_id: UUID of the ScheduledDose to confirm.
            caregiver_id: UUID of the authenticated caregiver (authorization check).
            notes: Optional clinical notes.

        Returns:
            DoseConfirmResponse with confirmation details.

        Raises:
            DoseNotFoundError: If the dose does not exist.
            MedicationNotFoundError: If the dose has no associated medication.
            ForbiddenError: If the caregiver does not own this patient.
            DoseAlreadyConfirmedError: If the dose was already confirmed.
        """
        dose = self.dose_repo.find_by_id(dose_id)
        if dose is None:
            raise DoseNotFoundError(str(dose_id))

        medication = self.medication_repo.find_by_id(dose.medication_id)
        if medication is None:
            raise MedicationNotFoundError(str(dose.medication_id))

        # Authorization: verify the caregiver owns this patient
        if medication.patient.caregiver_id != caregiver_id:
            raise ForbiddenError("You do not have access to this patient's doses")

        if dose.status == DoseStatus.CONFIRMED.value:
            raise DoseAlreadyConfirmedError(str(dose_id))

        # Confirm the dose
        dose.status = DoseStatus.CONFIRMED.value
        dose.taken_at = datetime.now(UTC)
        dose.notes = notes

        # Decrement stock — never go below zero
        if medication.current_stock_units > 0:
            medication.current_stock_units -= 1

        # Create critical stock alert if stock is at or below minimum
        if medication.current_stock_units <= medication.minimum_stock_units:
            self._create_critical_stock_alert(medication)

        self.db.flush()

        return DoseConfirmResponse(
            dose_id=dose.id,
            medication_name=medication.generic_name,
            taken_at=dose.taken_at,
            remaining_stock=medication.current_stock_units,
        )

    def get_patient_adherence(self, patient_id: UUID, caregiver_id: UUID) -> PatientAdherenceResponse:
        """Calculate adherence rates for all of a patient's medications.

        Args:
            patient_id: UUID of the patient.
            caregiver_id: UUID of the authenticated caregiver (authorization check).

        Returns:
            PatientAdherenceResponse with per-medication and overall adherence.

        Raises:
            ForbiddenError: If the patient belongs to a different caregiver.
        """
        from app.core.exceptions import NotFoundError
        from app.repositories.patient_repo import ElderlyPatientRepository

        patient_repo = ElderlyPatientRepository(self.db)
        patient = patient_repo.find_by_id(patient_id)
        if patient is None:
            raise NotFoundError("Patient not found")
        if patient.caregiver_id != caregiver_id:
            raise ForbiddenError("You do not have access to this patient")

        medications = self.medication_repo.find_all_by_patient(patient_id)
        medication_reports = []

        for medication in medications:
            stats = self.dose_repo.calculate_adherence_stats(medication.id)
            confirmed = stats[DoseStatus.CONFIRMED]
            missed = stats[DoseStatus.MISSED]
            pending = stats[DoseStatus.PENDING]
            total = confirmed + missed + pending

            adherence_pct = round((confirmed / total) * 100, 2) if total > 0 else 0.0

            medication_reports.append(
                AdherenceRateResponse(
                    medication_id=medication.id,
                    generic_name=medication.generic_name,
                    adherence_percentage=adherence_pct,
                    confirmed_count=confirmed,
                    missed_count=missed,
                    total_scheduled=total,
                )
            )

        overall = (
            round(
                sum(r.adherence_percentage for r in medication_reports)
                / len(medication_reports),
                2,
            )
            if medication_reports
            else 0.0
        )

        return PatientAdherenceResponse(
            patient_id=patient_id,
            overall_adherence=overall,
            medications=medication_reports,
        )

    def _create_critical_stock_alert(self, medication: object) -> None:
        """Create a critical stock alert for a medication.

        Args:
            medication: MedicationModel instance with low stock.
        """
        alert = MedicationAlertModel(
            patient_id=medication.patient_id,
            medication_id=medication.id,
            alert_type=AlertType.CRITICAL_STOCK.value,
            channel=AlertChannel.EMAIL.value,
            message=(
                f"Critical stock alert: {medication.generic_name} has "
                f"{medication.current_stock_units} units remaining "
                f"(minimum: {medication.minimum_stock_units})."
            ),
            sent_at=datetime.now(UTC),
            is_acknowledged=False,
        )
        self.alert_repo.save(alert)
