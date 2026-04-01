"""MedicalReportService - generate monthly PDF reports using fpdf2."""

from datetime import UTC, datetime
from uuid import UUID

from fpdf import FPDF
from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenError, NotFoundError
from app.domain.enums import DoseStatus
from app.repositories.alert_repo import AlertRepository
from app.repositories.dose_repo import ScheduledDoseRepository
from app.repositories.medication_repo import MedicationRepository
from app.repositories.patient_repo import ElderlyPatientRepository
from app.schemas.dose import AdherenceRateResponse


class MedicalReportService:
    """Generates a downloadable monthly PDF medical report for a patient.

    The report includes: patient info, active medications, adherence stats,
    and alert history for the last 30 days.

    Uses fpdf2 (pure Python, no system dependencies) instead of WeasyPrint
    which requires GTK on Windows.
    """

    def __init__(self, db: Session) -> None:
        self.patient_repo = ElderlyPatientRepository(db)
        self.medication_repo = MedicationRepository(db)
        self.dose_repo = ScheduledDoseRepository(db)
        self.alert_repo = AlertRepository(db)

    def generate_monthly_medical_report(
        self, patient_id: UUID, caregiver_id: UUID
    ) -> bytes:
        """Build and return a PDF report as bytes.

        Args:
            patient_id: UUID of the patient.
            caregiver_id: UUID of the authenticated caregiver (authorization check).

        Returns:
            PDF file content as bytes.

        Raises:
            NotFoundError: If the patient does not exist.
            ForbiddenError: If the patient belongs to a different caregiver.
        """
        patient = self.patient_repo.find_by_id(patient_id)
        if patient is None:
            raise NotFoundError("Patient not found")
        if patient.caregiver_id != caregiver_id:
            raise ForbiddenError("You do not have access to this patient")

        medications = self.medication_repo.find_all_by_patient(patient_id)
        alerts = self.alert_repo.find_last_month_by_patient(patient_id)

        adherence_list: list[AdherenceRateResponse] = []
        for med in medications:
            stats = self.dose_repo.calculate_adherence_stats(med.id, days=30)
            confirmed = stats[DoseStatus.CONFIRMED]
            missed = stats[DoseStatus.MISSED]
            pending = stats[DoseStatus.PENDING]
            total = confirmed + missed + pending
            pct = round((confirmed / total) * 100, 1) if total > 0 else 0.0
            adherence_list.append(
                AdherenceRateResponse(
                    medication_id=med.id,
                    generic_name=med.generic_name,
                    adherence_percentage=pct,
                    confirmed_count=confirmed,
                    missed_count=missed,
                    total_scheduled=total,
                )
            )

        return self._build_pdf(patient, adherence_list, alerts)

    # ------------------------------------------------------------------
    # PDF construction
    # ------------------------------------------------------------------

    def _build_pdf(self, patient: object, adherence_list: list, alerts: list) -> bytes:
        from app.models.patient import ElderlyPatientModel
        assert isinstance(patient, ElderlyPatientModel)

        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()

        # ── Header ──────────────────────────────────────────────────────
        pdf.set_font("Helvetica", "B", 20)
        pdf.set_fill_color(15, 107, 59)   # dark green
        pdf.set_text_color(255, 255, 255)
        pdf.cell(0, 14, "CareSync - Monthly Medical Report", align="C", fill=True, new_x="LMARGIN", new_y="NEXT")

        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Helvetica", "", 10)
        now = datetime.now(UTC)
        pdf.cell(0, 6, f"Generated: {now.strftime('%B %d, %Y at %H:%M UTC')}", align="C", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(6)

        # ── Patient info ─────────────────────────────────────────────────
        pdf.set_font("Helvetica", "B", 13)
        pdf.set_fill_color(235, 245, 235)
        pdf.cell(0, 9, "Patient Information", fill=True, new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 11)
        pdf.cell(0, 7, f"Name:         {patient.full_name}", new_x="LMARGIN", new_y="NEXT")
        pdf.cell(0, 7, f"Room:         {patient.room_number or 'N/A'}", new_x="LMARGIN", new_y="NEXT")
        pdf.cell(0, 7, f"Date of Birth: {patient.date_of_birth}", new_x="LMARGIN", new_y="NEXT")
        if patient.emergency_contact_name:
            pdf.cell(0, 7, f"Emergency Contact: {patient.emergency_contact_name} - {patient.emergency_contact_phone or ''}", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(5)

        # ── Medications & Adherence ──────────────────────────────────────
        pdf.set_font("Helvetica", "B", 13)
        pdf.set_fill_color(235, 245, 235)
        pdf.cell(0, 9, "Active Medications & Adherence (Last 30 Days)", fill=True, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)

        if not adherence_list:
            pdf.set_font("Helvetica", "I", 10)
            pdf.cell(0, 7, "No active medications.", new_x="LMARGIN", new_y="NEXT")
        else:
            # Table header
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_fill_color(200, 230, 200)
            col_w = [55, 25, 30, 25, 25, 30]
            headers = ["Medication", "Dose", "Adherence", "Confirmed", "Missed", "Scheduled"]
            for i, h in enumerate(headers):
                pdf.cell(col_w[i], 8, h, border=1, fill=True)
            pdf.ln()

            pdf.set_font("Helvetica", "", 10)
            for row in adherence_list:
                color = self._adherence_color(row.adherence_percentage)
                pdf.set_text_color(*color)
                pdf.cell(col_w[0], 7, row.generic_name[:28], border=1)
                pdf.set_text_color(0, 0, 0)
                pdf.cell(col_w[1], 7, "-", border=1)
                pdf.set_text_color(*color)
                pdf.cell(col_w[2], 7, f"{row.adherence_percentage:.1f}%", border=1, align="C")
                pdf.set_text_color(0, 0, 0)
                pdf.cell(col_w[3], 7, str(row.confirmed_count), border=1, align="C")
                pdf.cell(col_w[4], 7, str(row.missed_count), border=1, align="C")
                pdf.cell(col_w[5], 7, str(row.total_scheduled), border=1, align="C")
                pdf.ln()

        pdf.ln(5)

        # ── Alert history ────────────────────────────────────────────────
        pdf.set_font("Helvetica", "B", 13)
        pdf.set_fill_color(235, 245, 235)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(0, 9, f"Alert History - Last 30 Days ({len(alerts)} alerts)", fill=True, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)

        if not alerts:
            pdf.set_font("Helvetica", "I", 10)
            pdf.cell(0, 7, "No alerts in this period.", new_x="LMARGIN", new_y="NEXT")
        else:
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_fill_color(200, 230, 200)
            pdf.cell(40, 8, "Date", border=1, fill=True)
            pdf.cell(45, 8, "Type", border=1, fill=True)
            pdf.cell(105, 8, "Message", border=1, fill=True)
            pdf.ln()
            pdf.set_font("Helvetica", "", 9)
            for alert in alerts[:20]:  # max 20 rows
                date_str = alert.sent_at.strftime("%Y-%m-%d %H:%M")
                alert_type = alert.alert_type.replace("_", " ").title()
                msg = alert.message[:60] + ("…" if len(alert.message) > 60 else "")
                pdf.cell(40, 6, date_str, border=1)
                pdf.cell(45, 6, alert_type, border=1)
                pdf.cell(105, 6, msg, border=1)
                pdf.ln()

        # ── Footer ───────────────────────────────────────────────────────
        pdf.ln(8)
        pdf.set_font("Helvetica", "I", 9)
        pdf.set_text_color(120, 120, 120)
        pdf.cell(0, 6, "This report was generated automatically by CareSync API. Present to your physician at the next visit.", align="C", new_x="LMARGIN", new_y="NEXT")

        return bytes(pdf.output())

    @staticmethod
    def _adherence_color(pct: float) -> tuple[int, int, int]:
        """Return RGB color based on adherence level: green / orange / red."""
        if pct >= 80:
            return (15, 107, 59)   # green
        if pct >= 50:
            return (180, 83, 9)    # orange
        return (153, 27, 27)       # red
