"""Unit tests for domain exceptions — covers all constructors with/without args."""

from app.core.exceptions import (
    AppException,
    CaregiverNotFoundError,
    ConflictError,
    DomainValidationError,
    DoseAlreadyConfirmedError,
    DoseNotFoundError,
    EmailAlreadyRegisteredError,
    ExternalServiceError,
    ForbiddenError,
    InsufficientStockError,
    InvalidCredentialsError,
    MedicationExpiredError,
    MedicationNotFoundError,
    NotFoundError,
    PatientNotFoundError,
)

# ---------------------------------------------------------------------------
# AppException (base)
# ---------------------------------------------------------------------------


class TestAppException:
    def test_default_message(self) -> None:
        exc = AppException()
        assert exc.message == "An application error occurred."
        assert str(exc) == "An application error occurred."

    def test_custom_message(self) -> None:
        exc = AppException("custom")
        assert exc.message == "custom"

    def test_is_exception(self) -> None:
        assert isinstance(AppException(), Exception)


# ---------------------------------------------------------------------------
# 404 — Not Found
# ---------------------------------------------------------------------------


class TestNotFoundError:
    def test_default_message(self) -> None:
        exc = NotFoundError()
        assert exc.message == "Resource not found."

    def test_custom_message(self) -> None:
        exc = NotFoundError("Custom not found")
        assert exc.message == "Custom not found"

    def test_is_app_exception(self) -> None:
        assert isinstance(NotFoundError(), AppException)


class TestPatientNotFoundError:
    def test_with_patient_id(self) -> None:
        exc = PatientNotFoundError("abc-123")
        assert "abc-123" in exc.message
        assert "Patient" in exc.message

    def test_without_patient_id(self) -> None:
        exc = PatientNotFoundError()
        assert exc.message == "Patient not found."

    def test_none_patient_id(self) -> None:
        exc = PatientNotFoundError(None)
        assert exc.message == "Patient not found."

    def test_is_not_found_error(self) -> None:
        assert isinstance(PatientNotFoundError(), NotFoundError)


class TestCaregiverNotFoundError:
    def test_with_identifier(self) -> None:
        exc = CaregiverNotFoundError("john@example.com")
        assert "john@example.com" in exc.message

    def test_without_identifier(self) -> None:
        exc = CaregiverNotFoundError()
        assert exc.message == "Caregiver not found."

    def test_none_identifier(self) -> None:
        exc = CaregiverNotFoundError(None)
        assert exc.message == "Caregiver not found."


class TestMedicationNotFoundError:
    def test_with_medication_id(self) -> None:
        exc = MedicationNotFoundError("med-456")
        assert "med-456" in exc.message

    def test_without_medication_id(self) -> None:
        exc = MedicationNotFoundError()
        assert exc.message == "Medication not found."

    def test_none_medication_id(self) -> None:
        exc = MedicationNotFoundError(None)
        assert exc.message == "Medication not found."


class TestDoseNotFoundError:
    def test_with_dose_id(self) -> None:
        exc = DoseNotFoundError("dose-789")
        assert "dose-789" in exc.message

    def test_without_dose_id(self) -> None:
        exc = DoseNotFoundError()
        assert exc.message == "Dose not found."

    def test_none_dose_id(self) -> None:
        exc = DoseNotFoundError(None)
        assert exc.message == "Dose not found."


# ---------------------------------------------------------------------------
# 409 — Conflict
# ---------------------------------------------------------------------------


class TestConflictError:
    def test_default_message(self) -> None:
        exc = ConflictError()
        assert exc.message == "Resource conflict."

    def test_custom_message(self) -> None:
        exc = ConflictError("Already exists")
        assert exc.message == "Already exists"


class TestEmailAlreadyRegisteredError:
    def test_with_email(self) -> None:
        exc = EmailAlreadyRegisteredError("test@test.com")
        assert "test@test.com" in exc.message

    def test_without_email(self) -> None:
        exc = EmailAlreadyRegisteredError()
        assert exc.message == "Email is already registered."

    def test_none_email(self) -> None:
        exc = EmailAlreadyRegisteredError(None)
        assert exc.message == "Email is already registered."

    def test_is_conflict_error(self) -> None:
        assert isinstance(EmailAlreadyRegisteredError(), ConflictError)


class TestDoseAlreadyConfirmedError:
    def test_with_dose_id(self) -> None:
        exc = DoseAlreadyConfirmedError("dose-001")
        assert "dose-001" in exc.message
        assert "confirmed" in exc.message

    def test_without_dose_id(self) -> None:
        exc = DoseAlreadyConfirmedError()
        assert exc.message == "Dose has already been confirmed."

    def test_none_dose_id(self) -> None:
        exc = DoseAlreadyConfirmedError(None)
        assert exc.message == "Dose has already been confirmed."


# ---------------------------------------------------------------------------
# 422 — Domain Validation
# ---------------------------------------------------------------------------


class TestDomainValidationError:
    def test_default_message(self) -> None:
        exc = DomainValidationError()
        assert exc.message == "Domain validation failed."

    def test_custom_message(self) -> None:
        exc = DomainValidationError("Rule broken")
        assert exc.message == "Rule broken"


class TestMedicationExpiredError:
    def test_with_name(self) -> None:
        exc = MedicationExpiredError("Aspirin")
        assert "Aspirin" in exc.message
        assert "expired" in exc.message

    def test_without_name(self) -> None:
        exc = MedicationExpiredError()
        assert exc.message == "Medication has expired."

    def test_none_name(self) -> None:
        exc = MedicationExpiredError(None)
        assert exc.message == "Medication has expired."

    def test_is_domain_validation_error(self) -> None:
        assert isinstance(MedicationExpiredError(), DomainValidationError)


class TestInsufficientStockError:
    def test_with_name(self) -> None:
        exc = InsufficientStockError("Ibuprofen")
        assert "Ibuprofen" in exc.message
        assert "stock" in exc.message.lower()

    def test_without_name(self) -> None:
        exc = InsufficientStockError()
        assert exc.message == "Insufficient stock."

    def test_none_name(self) -> None:
        exc = InsufficientStockError(None)
        assert exc.message == "Insufficient stock."


class TestInvalidCredentialsError:
    def test_fixed_message(self) -> None:
        exc = InvalidCredentialsError()
        assert exc.message == "Invalid email or password."

    def test_is_domain_validation_error(self) -> None:
        assert isinstance(InvalidCredentialsError(), DomainValidationError)


# ---------------------------------------------------------------------------
# 403 — Forbidden
# ---------------------------------------------------------------------------


class TestForbiddenError:
    def test_default_message(self) -> None:
        exc = ForbiddenError()
        assert "permission" in exc.message.lower()

    def test_custom_message(self) -> None:
        exc = ForbiddenError("Access denied")
        assert exc.message == "Access denied"


# ---------------------------------------------------------------------------
# 503 — External Service
# ---------------------------------------------------------------------------


class TestExternalServiceError:
    def test_with_service_name(self) -> None:
        exc = ExternalServiceError(service="FDA API")
        assert "FDA API" in exc.message
        assert "unavailable" in exc.message

    def test_with_explicit_message(self) -> None:
        exc = ExternalServiceError(message="Custom error")
        assert exc.message == "Custom error"

    def test_message_takes_precedence_over_service(self) -> None:
        exc = ExternalServiceError(service="SomeService", message="Override message")
        assert exc.message == "Override message"

    def test_without_args(self) -> None:
        exc = ExternalServiceError()
        assert "unavailable" in exc.message

    def test_none_service(self) -> None:
        exc = ExternalServiceError(service=None)
        assert exc.message == "An external service is unavailable."

    def test_is_app_exception(self) -> None:
        assert isinstance(ExternalServiceError(), AppException)
