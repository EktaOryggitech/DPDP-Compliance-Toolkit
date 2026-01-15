"""
DPDP GUI Compliance Scanner - Organization Schemas
"""
from datetime import datetime
from typing import Optional
import uuid

from pydantic import BaseModel, EmailStr, Field


class OrganizationBase(BaseModel):
    """Base organization schema."""
    name: str = Field(min_length=2, max_length=255)
    code: Optional[str] = Field(None, max_length=50)
    type: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = None
    address: Optional[str] = None
    website: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = Field(None, max_length=20)
    dpo_name: Optional[str] = Field(None, max_length=255)
    dpo_email: Optional[EmailStr] = None
    dpo_phone: Optional[str] = Field(None, max_length=20)


class OrganizationCreate(OrganizationBase):
    """Organization creation schema."""
    pass


class OrganizationUpdate(BaseModel):
    """Organization update schema."""
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    code: Optional[str] = Field(None, max_length=50)
    type: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = None
    address: Optional[str] = None
    website: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = Field(None, max_length=20)
    dpo_name: Optional[str] = Field(None, max_length=255)
    dpo_email: Optional[EmailStr] = None
    dpo_phone: Optional[str] = Field(None, max_length=20)
    is_active: Optional[bool] = None


class OrganizationResponse(OrganizationBase):
    """Organization response schema."""
    id: uuid.UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime
    applications_count: Optional[int] = 0

    class Config:
        from_attributes = True
