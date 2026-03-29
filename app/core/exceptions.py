"""Domain exception hierarchy for MiMedicacion.

Services raise these exceptions; HTTP exception handlers in main.py
map them to appropriate HTTP status codes.  No FastAPI or HTTP
concepts should appear here.
"""


class AppException(Exception):
    """Base exception for all application domain errors."""

    def __init__(self, message: str = "An application error occurred.") -> None:
        self.message = message
        super().__init__(message)


# ---------------------------------------------------------------------------
# 404 — Not Found
# ---------------------------------------------------------------------------


class NotFoundError(AppException):
    """Raised when a requested resource does not exist."""

    def __init__(self, message: str = "Resource not found.") -> None:
        super().__init__(message)


class PatientNotFoundError(NotFoundError):
    """Raised when an ElderlyPatient cannot be located."""

    def __init__(self, patient_id: str | None = None) -> None:
        msg = (
            f"Patient with id '{patient_id}' not found."
            if patient_id
            else "Patient not found."
        )
        super().__init__(msg)


class CaregiverNotFoundError(NotFoundError):
    """Raised when a ResponsibleCaregiver cannot be located."""

    def __init__(self, identifier: str | None = None) -> None:
        msg = (
            f"Caregiver '{identifier}' not found."
            if identifier
            else "Caregiver not found."
        )
        super().__init__(msg)


class MedicationNotFoundError(NotFoundError):
    """Raised when a Medication record cannot be located."""

    def __init__(self, medication_id: str | None = None) -> None:
        msg = (
            f"Medication with id '{medication_id}' not found."
            if medication_id
            else "Medication not found."
        )
        super().__init__(msg)


class DoseNotFoundError(NotFoundError):
    """Raised when a ScheduledDose record cannot be located."""

    def __init__(self, dose_id: str | None = None) -> None:
        msg = (
            f"Dose with id '{dose_id}' not found."
            if dose_id
            else "Dose not found."
        )
        super().__init__(msg)


# ---------------------------------------------------------------------------
# 409 — Conflict
# ---------------------------------------------------------------------------


class ConflictError(AppException):
    """Raised when an action would violate a uniqueness or state constraint."""

    def __init__(self, message: str = "Resource conflict.") -> None:
        super().__init__(message)


class EmailAlreadyRegisteredError(ConflictError):
    """Raised when a registration attempt uses an already-registered e-mail."""

    def __init__(self, email: str | None = None) -> None:
        msg = (
            f"Email '{email}' is already registered."
            if email
            else "Email is already registered."
        )
        super().__init__(msg)


class DoseAlreadyConfirmedError(ConflictError):
    """Raised when attempting to confirm a dose that was already confirmed."""

    def __init__(self, dose_id: str | None = None) -> None:
        msg = (
            f"Dose '{dose_id}' has already been confirmed."
            if dose_id
            else "Dose has already been confirmed."
        )
        super().__init__(msg)


# ---------------------------------------------------------------------------
# 422 — Domain Validation
# ---------------------------------------------------------------------------


class DomainValidationError(AppException):
    """Raised when domain business rules are violated."""

    def __init__(self, message: str = "Domain validation failed.") -> None:
        super().__init__(message)


class MedicationExpiredError(DomainValidationError):
    """Raised when a dose is scheduled for an expired medication."""

    def __init__(self, medication_name: str | None = None) -> None:
        msg = (
            f"Medication '{medication_name}' has expired."
            if medication_name
            else "Medication has expired."
        )
        super().__init__(msg)


class InsufficientStockError(DomainValidationError):
    """Raised when medication stock is too low to schedule a dose."""

    def __init__(self, medication_name: str | None = None) -> None:
        msg = (
            f"Insufficient stock for medication '{medication_name}'."
            if medication_name
            else "Insufficient stock."
        )
        super().__init__(msg)


class InvalidCredentialsError(DomainValidationError):
    """Raised when authentication credentials are invalid."""

    def __init__(self) -> None:
        super().__init__("Invalid email or password.")


# ---------------------------------------------------------------------------
# 403 — Forbidden
# ---------------------------------------------------------------------------


class ForbiddenError(AppException):
    """Raised when the caller lacks permission to access a resource."""

    def __init__(self, message: str = "You do not have permission to perform this action.") -> None:
        super().__init__(message)


# ---------------------------------------------------------------------------
# 503 — External Service
# ---------------------------------------------------------------------------


class ExternalServiceError(AppException):
    """Raised when a downstream external service call fails."""

    def __init__(self, service: str | None = None, message: str | None = None) -> None:
        msg = message or (
            f"External service '{service}' is unavailable."
            if service
            else "An external service is unavailable."
        )
        super().__init__(msg)
