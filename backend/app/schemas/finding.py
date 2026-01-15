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
    title: str
    description: Optional[str]
    remediation: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class FindingDetail(FindingResponse):
    """Detailed finding response with evidence."""
    element_xpath: Optional[str]
    element_selector: Optional[str]
    metadata: Optional[Dict]
    evidence: List[EvidenceResponse] = []


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
