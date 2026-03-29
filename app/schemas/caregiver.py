"""Pydantic schemas for ResponsibleCaregiver endpoints."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class CaregiverRegistrationRequest(BaseModel):
    """Request body for POST /auth/register."""

    email: EmailStr
    password: Annotated[str, Field(min_length=8, max_length=128)]
    full_name: Annotated[str, Field(min_length=2, max_length=200)]


class CaregiverResponse(BaseModel):
    """Public representation of a ResponsibleCaregiver."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    full_name: str
    is_active: bool
    created_at: datetime


class TokenResponse(BaseModel):
    """JWT access token issued after successful authentication."""

    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    """Request body for POST /auth/login."""

    email: EmailStr
    password: str
