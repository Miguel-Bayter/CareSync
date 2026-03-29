"""Domain enumerations for MiMedicacion.

These are pure-Python enums with no framework dependencies.
"""

from enum import Enum


class DoseStatus(str, Enum):
    """Possible states for a scheduled medication dose."""

    PENDING = "pending"
    CONFIRMED = "confirmed"
    MISSED = "missed"


class AlertType(str, Enum):
    """Types of automated alerts the system can emit."""

    DOSE_REMINDER = "dose_reminder"
    URGENT_MISSED_DOSE = "urgent_missed_dose"
    CRITICAL_STOCK = "critical_stock"
    MEDICATION_EXPIRING = "medication_expiring"


class AlertChannel(str, Enum):
    """Delivery channels for alerts."""

    EMAIL = "email"
    WHATSAPP = "whatsapp"


class ChronicCondition(str, Enum):
    """Recognised chronic medical conditions for elderly patients."""

    DIABETES_TYPE2 = "diabetes_type2"
    HYPERTENSION = "hypertension"
    ALZHEIMERS = "alzheimers"
    PARKINSONS = "parkinsons"
    OSTEOPOROSIS = "osteoporosis"
    HEART_FAILURE = "heart_failure"
    CHRONIC_KIDNEY_DISEASE = "chronic_kidney_disease"
    COPD = "copd"
    DEPRESSION = "depression"
    ARTHRITIS = "arthritis"
