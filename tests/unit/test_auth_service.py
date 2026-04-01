"""Unit tests for CaregiverAuthService using mocked repositories."""

from datetime import UTC, datetime
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.core.exceptions import EmailAlreadyRegisteredError, InvalidCredentialsError
from app.core.security import hash_password
from app.models.caregiver import ResponsibleCaregiverModel
from app.services.auth_service import CaregiverAuthService


def _make_service(caregiver_repo: MagicMock) -> CaregiverAuthService:
    db = MagicMock()
    return CaregiverAuthService(caregiver_repo=caregiver_repo, db=db)


def _make_caregiver(email: str = "test@example.com", password: str = "Password123") -> ResponsibleCaregiverModel:
    caregiver = ResponsibleCaregiverModel()
    caregiver.id = uuid4()
    caregiver.email = email
    caregiver.full_name = "Test User"
    caregiver.hashed_password = hash_password(password)
    caregiver.is_active = True
    caregiver.created_at = datetime.now(UTC)
    caregiver.updated_at = datetime.now(UTC)
    return caregiver


class TestRegisterCaregiver:
    def test_raises_when_email_exists(self) -> None:
        """Should raise EmailAlreadyRegisteredError if e-mail is taken."""
        repo = MagicMock()
        repo.find_by_email.return_value = _make_caregiver()
        service = _make_service(repo)

        with pytest.raises(EmailAlreadyRegisteredError):
            service.register_caregiver(
                email="taken@example.com",
                password="Password123",
                full_name="Someone",
            )

    def test_creates_caregiver_successfully(self) -> None:
        """Should return a CaregiverResponse when the e-mail is available."""
        repo = MagicMock()
        repo.find_by_email.return_value = None
        saved = _make_caregiver()
        repo.save.return_value = saved
        service = _make_service(repo)

        result = service.register_caregiver(
            email="new@example.com",
            password="Password123",
            full_name="New User",
        )

        repo.save.assert_called_once()
        assert result.email == saved.email


class TestAuthenticateCaregiver:
    def test_returns_token_for_valid_credentials(self) -> None:
        """Should return a TokenResponse when credentials are correct."""
        password = "Password123"
        repo = MagicMock()
        repo.find_by_email.return_value = _make_caregiver(password=password)
        service = _make_service(repo)

        result = service.authenticate_caregiver(email="test@example.com", password=password)

        assert result.access_token
        assert result.token_type == "bearer"

    def test_raises_for_invalid_password(self) -> None:
        """Should raise InvalidCredentialsError when the password is wrong."""
        repo = MagicMock()
        repo.find_by_email.return_value = _make_caregiver(password="CorrectPassword")
        service = _make_service(repo)

        with pytest.raises(InvalidCredentialsError):
            service.authenticate_caregiver(email="test@example.com", password="WrongPassword")

    def test_raises_when_user_not_found(self) -> None:
        """Should raise InvalidCredentialsError when e-mail is not found."""
        repo = MagicMock()
        repo.find_by_email.return_value = None
        service = _make_service(repo)

        with pytest.raises(InvalidCredentialsError):
            service.authenticate_caregiver(email="nobody@example.com", password="Password123")
