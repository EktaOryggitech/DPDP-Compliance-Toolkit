"""
DPDP GUI Compliance Scanner - Authentication Schemas
"""
from typing import Optional
import uuid

from pydantic import BaseModel, EmailStr, Field

from app.models.user import UserRole


class LoginRequest(BaseModel):
    """Login request schema."""
    email: EmailStr
    password: str = Field(min_length=8)


class RegisterRequest(BaseModel):
    """User registration request schema."""
    email: EmailStr
    password: str = Field(min_length=8)
    name: str = Field(min_length=2, max_length=255)
    organization_id: Optional[uuid.UUID] = None
    role: UserRole = UserRole.VIEWER


class Token(BaseModel):
    """JWT token response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Access token expiry in seconds")


class TokenPayload(BaseModel):
    """JWT token payload."""
    sub: str
    exp: int
    type: str


class UserResponse(BaseModel):
    """User response schema."""
    id: uuid.UUID
    email: str
    name: str
    role: UserRole
    organization_id: Optional[uuid.UUID]
    is_active: bool
    is_verified: bool

    class Config:
        from_attributes = True


class PasswordChangeRequest(BaseModel):
    """Password change request."""
    current_password: str
    new_password: str = Field(min_length=8)
