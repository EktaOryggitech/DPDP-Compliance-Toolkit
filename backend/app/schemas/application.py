"""
DPDP GUI Compliance Scanner - Application Schemas
"""
from datetime import datetime
from typing import Dict, List, Optional
import uuid

from pydantic import BaseModel, Field, HttpUrl

from app.models.application import ApplicationType


class AuthConfig(BaseModel):
    """Authentication configuration for applications."""
    auth_type: str = Field(description="Type: none, manual, credentials, session, oauth")
    login_url: Optional[str] = None
    username_field: Optional[str] = None
    password_field: Optional[str] = None
    credentials: Optional[Dict[str, str]] = None  # Encrypted in storage
    session_cookies: Optional[Dict[str, str]] = None
    oauth_config: Optional[Dict[str, str]] = None


class ScanConfig(BaseModel):
    """Scan configuration for applications."""
    crawl_depth: int = Field(default=100, ge=1, le=500)
    timeout_seconds: int = Field(default=1800, ge=60, le=7200)
    include_patterns: Optional[List[str]] = None
    exclude_patterns: Optional[List[str]] = None
    follow_external_links: bool = False
    capture_screenshots: bool = True
    capture_html: bool = True
    mobile_viewport: bool = False


class ApplicationBase(BaseModel):
    """Base application schema."""
    name: str = Field(min_length=2, max_length=255)
    description: Optional[str] = None
    type: ApplicationType
    url: Optional[str] = Field(None, max_length=2048)
    executable_path: Optional[str] = None
    window_title: Optional[str] = None
    tags: Optional[List[str]] = []


class ApplicationCreate(ApplicationBase):
    """Application creation schema."""
    organization_id: uuid.UUID
    auth_config: Optional[AuthConfig] = None
    scan_config: Optional[ScanConfig] = None


class ApplicationUpdate(BaseModel):
    """Application update schema."""
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    description: Optional[str] = None
    url: Optional[str] = Field(None, max_length=2048)
    executable_path: Optional[str] = None
    window_title: Optional[str] = None
    auth_config: Optional[AuthConfig] = None
    scan_config: Optional[ScanConfig] = None
    tags: Optional[List[str]] = None
    is_active: Optional[bool] = None


class ApplicationResponse(ApplicationBase):
    """Application response schema."""
    id: uuid.UUID
    organization_id: uuid.UUID
    auth_config: Optional[Dict] = None
    scan_config: Optional[Dict] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    last_scan_at: Optional[datetime] = None
    last_scan_score: Optional[float] = None
    scans_count: Optional[int] = 0

    class Config:
        from_attributes = True
