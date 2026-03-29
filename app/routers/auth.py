"""Authentication router — register and login endpoints."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.repositories.caregiver_repo import CaregiverRepository
from app.schemas.caregiver import (
    CaregiverRegistrationRequest,
    CaregiverResponse,
    LoginRequest,
    TokenResponse,
)
from app.services.auth_service import CaregiverAuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _get_auth_service(db: Session = Depends(get_db)) -> CaregiverAuthService:
    return CaregiverAuthService(caregiver_repo=CaregiverRepository(db), db=db)


@router.post(
    "/register",
    response_model=CaregiverResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new responsible caregiver",
)
def register(
    body: CaregiverRegistrationRequest,
    service: CaregiverAuthService = Depends(_get_auth_service),
) -> CaregiverResponse:
    """Create a new caregiver account.

    Args:
        body: Registration request with email, password, and full name.
        service: Injected auth service.

    Returns:
        The newly created caregiver's public profile.
    """
    return service.register_caregiver(
        email=body.email,
        password=body.password,
        full_name=body.full_name,
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Authenticate and receive a JWT access token",
)
def login(
    body: LoginRequest,
    service: CaregiverAuthService = Depends(_get_auth_service),
) -> TokenResponse:
    """Authenticate a caregiver and return a signed JWT token.

    Accepts a JSON body with ``email`` and ``password``.

    Args:
        body: Login credentials.
        service: Injected auth service.

    Returns:
        A bearer token response.
    """
    return service.authenticate_caregiver(email=body.email, password=body.password)
