"""
DPDP GUI Compliance Scanner - Finding Schemas
"""
from datetime import datetime
from typing import Dict, List, Optional
import uuid

from pydantic import BaseModel

from app.models.finding import CheckType, FindingSeverity, FindingStatus


class EvidenceResponse(BaseModel):
    """Evidence response schema."""
    id: uuid.UUID
    type: str
    storage_path: str
    file_name: Optional[str]
    mime_type: Optional[str]
    annotations: Optional[Dict]
    text_content: Optional[str]

    class Config:
        from_attributes = True


class FindingResponse(BaseModel):
    """Finding response schema."""
    id: uuid.UUID
    scan_id: uuid.UUID
    check_type: CheckType
    dpdp_section: Optional[str]
    status: FindingStatus
    severity: FindingSeverity
    confidence: Optional[float]
    location: Optional[str]
    element_selector: Optional[str] = None
    title: str
    description: Optional[str]
    remediation: Optional[str]
    extra_data: Optional[Dict] = None  # Detailed finding data (code fixes, visual representation, etc.)
    created_at: datetime

    class Config:
        from_attributes = True


class FindingDetail(FindingResponse):
    """Detailed finding response with evidence and extra data."""
    element_xpath: Optional[str]
    element_selector: Optional[str]
    extra_data: Optional[Dict] = None  # Detailed finding data (code_before, code_after, visual, etc.)
    metadata: Optional[Dict] = None
    evidence: List[EvidenceResponse] = []

    # Computed fields for easy access
    @property
    def code_before(self) -> Optional[str]:
        """Get code before fix from extra_data."""
        return self.extra_data.get("code_before") if self.extra_data else None

    @property
    def code_after(self) -> Optional[str]:
        """Get code after fix from extra_data."""
        return self.extra_data.get("code_after") if self.extra_data else None

    @property
    def visual_representation(self) -> Optional[str]:
        """Get visual ASCII diagram from extra_data."""
        return self.extra_data.get("visual_representation") if self.extra_data else None

    @property
    def fix_steps(self) -> Optional[List[str]]:
        """Get remediation steps from extra_data."""
        return self.extra_data.get("fix_steps") if self.extra_data else None

    @property
    def penalty_risk(self) -> Optional[str]:
        """Get penalty risk from extra_data."""
        return self.extra_data.get("penalty_risk") if self.extra_data else None

    @property
    def dpdp_reference(self) -> Optional[Dict]:
        """Get DPDP reference details from extra_data."""
        return self.extra_data.get("dpdp_reference") if self.extra_data else None


class FindingsBySection(BaseModel):
    """Findings grouped by DPDP section."""
    section: str
    section_name: str
    total: int
    passed: int
    failed: int
    partial: int
    findings: List[FindingResponse]


class ComplianceScoreBreakdown(BaseModel):
    """Compliance score breakdown by section."""
    section_5_privacy_notice: Optional[float] = None
    section_6_consent: Optional[float] = None
    section_6_6_withdrawal: Optional[float] = None
    section_9_children: Optional[float] = None
    section_11_14_rights: Optional[float] = None
    dark_patterns: Optional[float] = None
    overall: Optional[float] = None


class FindingSummary(BaseModel):
    """Lightweight finding summary for page-wise display."""
    id: uuid.UUID
    title: str
    severity: FindingSeverity
    status: FindingStatus
    check_type: CheckType
    dpdp_section: Optional[str]
    description: Optional[str]
    remediation: Optional[str] = None
    element_selector: Optional[str] = None
    extra_data: Optional[Dict] = None  # Detailed finding data

    class Config:
        from_attributes = True


class FindingsByPage(BaseModel):
    """Findings grouped by page/URL."""
    page_url: str
    page_title: Optional[str] = None
    findings_count: int
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    info_count: int = 0
    findings: List[FindingSummary]
