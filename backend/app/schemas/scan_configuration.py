"""
DPDP GUI Compliance Scanner - Scan Configuration Schemas
"""
from datetime import datetime
from typing import Optional
import uuid

from pydantic import BaseModel, Field


# Configuration bounds (fixed)
QUICK_MIN = 10
QUICK_MAX = 50
QUICK_DEFAULT = 20

STANDARD_MIN = 50
STANDARD_MAX = 150
STANDARD_DEFAULT = 75

DEEP_MIN = 150
DEEP_MAX = 500
DEEP_DEFAULT = 200


class ScanConfigurationUpdate(BaseModel):
    """Schema for updating scan configuration."""
    quick_pages: Optional[int] = Field(None, ge=QUICK_MIN, le=QUICK_MAX)
    standard_pages: Optional[int] = Field(None, ge=STANDARD_MIN, le=STANDARD_MAX)
    deep_pages: Optional[int] = Field(None, ge=DEEP_MIN, le=DEEP_MAX)


class ScanConfigurationResponse(BaseModel):
    """Schema for scan configuration response."""
    id: uuid.UUID
    quick_pages: int
    standard_pages: int
    deep_pages: int
    created_at: datetime
    updated_at: datetime

    # Include bounds for frontend validation
    quick_min: int = QUICK_MIN
    quick_max: int = QUICK_MAX
    standard_min: int = STANDARD_MIN
    standard_max: int = STANDARD_MAX
    deep_min: int = DEEP_MIN
    deep_max: int = DEEP_MAX

    class Config:
        from_attributes = True
