"""
DPDP GUI Compliance Scanner - Scan Schemas
"""
from datetime import datetime
from typing import Dict, List, Optional
import uuid

from pydantic import BaseModel, Field

from app.models.scan import ScanStatus, ScanType
from app.schemas.finding import FindingsByPage


class ScanCreate(BaseModel):
    """Scan creation request schema."""
    application_id: uuid.UUID
    scan_type: ScanType = ScanType.STANDARD
    config_overrides: Optional[Dict] = None  # Override application scan config


class ScanProgress(BaseModel):
    """Scan progress update schema (for WebSocket and polling)."""
    scan_id: uuid.UUID
    status: str
    percent: int = 0
    pages_scanned: int = 0
    total_pages: Optional[int] = None
    current_url: Optional[str] = None
    message: Optional[str] = None
    findings_count: int = 0
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    elapsed_seconds: Optional[int] = None
    estimated_remaining_seconds: Optional[int] = None


class ScanSummary(BaseModel):
    """Scan summary for dashboard."""
    total_scans: int
    completed_scans: int
    running_scans: int
    failed_scans: int
    average_score: Optional[float]
    critical_findings: int
    high_findings: int
    medium_findings: int
    low_findings: int


class ScanResponse(BaseModel):
    """Scan response schema."""
    id: uuid.UUID
    application_id: uuid.UUID
    application_name: Optional[str] = None
    scan_type: ScanType
    status: ScanStatus
    status_message: Optional[str]
    progress_percentage: int
    pages_scanned: int
    total_pages: Optional[int]
    current_url: Optional[str]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    duration_seconds: Optional[int]
    overall_score: Optional[float]
    findings_count: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    scan_config: Optional[Dict]
    created_at: datetime

    class Config:
        from_attributes = True


class ScanDetailResponse(ScanResponse):
    """Detailed scan response with findings summary."""
    findings_by_section: Optional[Dict[str, int]] = None
    findings_by_type: Optional[Dict[str, int]] = None
    findings_by_page: Optional[List[FindingsByPage]] = None
    compliance_breakdown: Optional[Dict[str, Dict]] = None
