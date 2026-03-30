# Import all models here so SQLAlchemy can resolve string-based relationships.
# Order matters: independent models first, then models with foreign keys.
from app.models.caregiver import ResponsibleCaregiverModel
from app.models.patient import ElderlyPatientModel
from app.models.medication import MedicationModel
from app.models.dose import ScheduledDoseModel
from app.models.alert import MedicationAlertModel

__all__ = [
    "ResponsibleCaregiverModel",
    "ElderlyPatientModel",
    "MedicationModel",
    "ScheduledDoseModel",
    "MedicationAlertModel",
]
