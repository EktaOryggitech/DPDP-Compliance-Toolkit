"""
DPDP GUI Compliance Scanner - Findings API Routes
"""
from typing import List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, DbSession
from app.models.finding import Finding, FindingSeverity, FindingStatus, CheckType
from app.models.evidence import Evidence
from app.schemas.finding import (
    FindingResponse,
    FindingDetail,
    FindingsBySection,
    EvidenceResponse,
)
from app.schemas.common import PaginatedResponse, PaginationParams

router = APIRouter()


def get_screenshot_url(screenshot_path: Optional[str]) -> Optional[str]:
    """Generate proxy URL for a screenshot if it exists.

    Instead of using MinIO presigned URLs (which have signature issues
    when accessed from browser), we use a proxy endpoint that serves
    the image through the backend.
    """
    if not screenshot_path:
        return None

    try:
        # Convert MinIO path to proxy URL
        # Path format: scans/{scan_id}/{year}/{month}/{day}/{filename}.jpg
        # URL format: /api/v1/evidence/screenshot/{scan_id}/{year}/{month}/{day}/{filename}.jpg
        if screenshot_path.startswith("scans/"):
            return f"/api/v1/evidence/screenshot/{screenshot_path[6:]}"
        return None
    except Exception as e:
        print(f"Error generating screenshot URL: {e}")
        return None


def enrich_finding_with_screenshot(finding: Finding) -> FindingResponse:
    """Convert finding to response with screenshot URL."""
    response = FindingResponse.model_validate(finding)
    if finding.screenshot_path:
        response.screenshot_url = get_screenshot_url(finding.screenshot_path)
    return response


@router.get("", response_model=PaginatedResponse[FindingResponse])
async def list_findings(
    db: DbSession,
    current_user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    scan_id: Optional[uuid.UUID] = None,
    severity: Optional[FindingSeverity] = None,
    status: Optional[FindingStatus] = None,
    check_type: Optional[CheckType] = None,
    dpdp_section: Optional[str] = None,
):
    """
    List findings (with pagination and filters).
    """
    query = select(Finding)

    if scan_id:
        query = query.where(Finding.scan_id == scan_id)

    if severity:
        query = query.where(Finding.severity == severity)

    if status:
        query = query.where(Finding.status == status)

    if check_type:
        query = query.where(Finding.check_type == check_type)

    if dpdp_section:
        query = query.where(Finding.dpdp_section == dpdp_section)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)

    # Apply pagination
    query = query.offset((page - 1) * page_size).limit(page_size)
    query = query.order_by(Finding.severity, Finding.created_at.desc())

    result = await db.execute(query)
    findings = result.scalars().all()

    # Enrich findings with screenshot URLs
    enriched_findings = []
    for f in findings:
        enriched = enrich_finding_with_screenshot(f)
        enriched_findings.append(enriched)

    return PaginatedResponse.create(
        items=enriched_findings,
        total=total,
        params=PaginationParams(page=page, page_size=page_size),
    )


@router.get("/{finding_id}", response_model=FindingDetail)
async def get_finding(
    finding_id: uuid.UUID,
    db: DbSession,
    current_user: CurrentUser,
):
    """
    Get finding details with evidence.
    """
    result = await db.execute(select(Finding).where(Finding.id == finding_id))
    finding = result.scalar_one_or_none()

    if not finding:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Finding not found",
        )

    # Get evidence
    evidence_result = await db.execute(
        select(Evidence).where(Evidence.finding_id == finding_id)
    )
    evidence = evidence_result.scalars().all()

    response = FindingDetail.model_validate(finding)
    response.evidence = [EvidenceResponse.model_validate(e) for e in evidence]

    # Add screenshot URL if available
    if finding.screenshot_path:
        response.screenshot_url = get_screenshot_url(finding.screenshot_path)

    return response


@router.get("/by-scan/{scan_id}/grouped", response_model=List[FindingsBySection])
async def get_findings_grouped_by_section(
    scan_id: uuid.UUID,
    db: DbSession,
    current_user: CurrentUser,
):
    """
    Get findings for a scan grouped by DPDP section.
    """
    result = await db.execute(
        select(Finding)
        .where(Finding.scan_id == scan_id)
        .order_by(Finding.dpdp_section, Finding.severity)
    )
    findings = result.scalars().all()

    # Group by section
    sections_map = {
        "Section 5": "Privacy Notice",
        "Section 6": "Consent Mechanism",
        "Section 6(6)": "Withdrawal Mechanism",
        "Section 9": "Children's Data",
        "Section 11": "Right to Access",
        "Section 12": "Right to Correction/Erasure",
        "Section 13": "Grievance Redressal",
        "Section 14": "Right to Nominate",
        "Dark Patterns": "Dark Pattern Detection",
    }

    grouped = {}
    for finding in findings:
        section = finding.dpdp_section or "Other"
        if section not in grouped:
            grouped[section] = {
                "section": section,
                "section_name": sections_map.get(section, section),
                "total": 0,
                "passed": 0,
                "failed": 0,
                "partial": 0,
                "findings": [],
            }

        grouped[section]["total"] += 1
        enriched = enrich_finding_with_screenshot(finding)
        grouped[section]["findings"].append(enriched)

        if finding.status == FindingStatus.PASS:
            grouped[section]["passed"] += 1
        elif finding.status == FindingStatus.FAIL:
            grouped[section]["failed"] += 1
        elif finding.status == FindingStatus.PARTIAL:
            grouped[section]["partial"] += 1

    return [FindingsBySection(**data) for data in grouped.values()]
