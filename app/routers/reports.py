"""Reports router — generate downloadable medical PDF reports."""

from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import CaregiverDep
from app.services.medical_report_service import MedicalReportService

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get(
    "/{patient_id}/medical-pdf",
    response_class=Response,
    summary="Download the monthly medical PDF report for a patient",
    responses={
        200: {
            "content": {"application/pdf": {}},
            "description": "PDF report downloaded successfully.",
        }
    },
)
def get_medical_pdf_report(
    patient_id: UUID,
    current_caregiver: CaregiverDep,
    db: Session = Depends(get_db),
) -> Response:
    """Generate and return a PDF with the patient's medication adherence report.

    The PDF includes patient info, active medications, adherence percentages
    (color-coded: green ≥80%, orange ≥50%, red <50%), and the last 30 days
    of alert history.

    Args:
        patient_id: UUID of the patient.
        current_caregiver: Authenticated caregiver from JWT.
        db: Database session.

    Returns:
        PDF file as a downloadable attachment.
    """
    from datetime import UTC, datetime

    service = MedicalReportService(db=db)
    pdf_bytes = service.generate_monthly_medical_report(
        patient_id=patient_id,
        caregiver_id=current_caregiver.id,
    )

    now = datetime.now(UTC)
    filename = f"medical_report_{now.strftime('%Y_%m')}_patient_{str(patient_id)[:8]}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
