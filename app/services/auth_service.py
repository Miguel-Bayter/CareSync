"""Business logic for caregiver authentication and registration."""

import structlog
from sqlalchemy.orm import Session

from app.core.exceptions import EmailAlreadyRegisteredError, InvalidCredentialsError
from app.core.security import create_access_token, hash_password, verify_password
from app.models.caregiver import ResponsibleCaregiverModel
from app.repositories.caregiver_repo import CaregiverRepository
from app.schemas.caregiver import CaregiverResponse, TokenResponse

logger = structlog.get_logger(__name__)


class CaregiverAuthService:
    """Service that handles caregiver registration and authentication.

    Args:
        caregiver_repo: Repository for caregiver persistence.
        db: Active SQLAlchemy Session (owned by the request lifecycle).
    """

    def __init__(self, caregiver_repo: CaregiverRepository, db: Session) -> None:
        self._repo = caregiver_repo
        self._db = db

    def register_caregiver(
        self,
        email: str,
        password: str,
        full_name: str,
    ) -> CaregiverResponse:
        """Register a new responsible caregiver.

        Args:
            email: Unique e-mail address for the new account.
            password: Plain-text password (will be hashed before storage).
            full_name: Display name of the caregiver.

        Returns:
            The created CaregiverResponse schema.

        Raises:
            EmailAlreadyRegisteredError: If the e-mail is already in use.
        """
        existing = self._repo.find_by_email(email)
        if existing is not None:
            raise EmailAlreadyRegisteredError(email)

        caregiver = ResponsibleCaregiverModel(
            email=email,
            full_name=full_name,
            hashed_password=hash_password(password),
        )
        saved = self._repo.save(caregiver)
        logger.info("caregiver_registered", caregiver_id=str(saved.id))
        return CaregiverResponse.model_validate(saved)

    def authenticate_caregiver(self, email: str, password: str) -> TokenResponse:
        """Authenticate a caregiver by e-mail and password.

        Args:
            email: The caregiver's registered e-mail address.
            password: The plain-text password to verify.

        Returns:
            A TokenResponse containing the signed JWT access token.

        Raises:
            InvalidCredentialsError: If the e-mail is not found or the
                password does not match.
        """
        caregiver = self._repo.find_by_email(email)
        if caregiver is None:
            raise InvalidCredentialsError()

        if not verify_password(password, caregiver.hashed_password):
            raise InvalidCredentialsError()

        token = create_access_token(str(caregiver.id))
        logger.info("caregiver_authenticated", caregiver_id=str(caregiver.id))
        return TokenResponse(access_token=token)
