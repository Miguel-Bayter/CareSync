"""FastAPI dependency injection helpers."""

from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.database import get_db
from app.models.caregiver import ResponsibleCaregiverModel

http_bearer = HTTPBearer()

DbDep = Annotated[Session, Depends(get_db)]


def get_current_caregiver(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(http_bearer)],
    db: DbDep,
) -> ResponsibleCaregiverModel:
    """Decode the JWT and return the authenticated caregiver.

    Args:
        token: Bearer token from the Authorization header.
        db: Injected database session.

    Returns:
        The authenticated ResponsibleCaregiverModel.

    Raises:
        HTTPException 401: If the token is invalid or the user no longer exists.
    """
    subject = decode_access_token(credentials.credentials)
    if subject is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    from app.repositories.caregiver_repo import CaregiverRepository

    caregiver = CaregiverRepository(db).find_by_id(UUID(subject))
    if caregiver is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return caregiver


CaregiverDep = Annotated[ResponsibleCaregiverModel, Depends(get_current_caregiver)]
