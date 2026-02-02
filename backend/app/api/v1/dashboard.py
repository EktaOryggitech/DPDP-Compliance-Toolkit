"""
DPDP GUI Compliance Scanner - Dashboard API Routes

Provides aggregated data for the dashboard view.
"""
from typing import List, Optional
import uuid

from fastapi import APIRouter
from sqlalchemy import func, select
from pydantic import BaseModel

from app.api.deps import CurrentUser, DbSession
from app.models.scan import Scan, ScanStatus
from app.models.finding import Finding, FindingSeverity
from app.models.application import Application

router = APIRouter()


class DashboardStats(BaseModel):
    """Dashboard statistics."""
    total_scans: int
    critical_findings: int
    compliant_apps: int  # Apps with score >= 80
    pending_scans: int  # Running + Queued scans


class FindingsBySectionItem(BaseModel):
    """Findings count for a DPDP section."""
    name: str
    findings: int


class FindingsBySeverityItem(BaseModel):
    """Findings count for a severity level."""
    name: str
    value: int


class DashboardData(BaseModel):
    """Complete dashboard data."""
    stats: DashboardStats
    findings_by_section: List[FindingsBySectionItem]
    findings_by_severity: List[FindingsBySeverityItem]


@router.get("", response_model=DashboardData)
async def get_dashboard_data(
    db: DbSession,
    current_user: CurrentUser,
):
    """
    Get all dashboard data in a single request.
    """
    # --- Stats ---

    # Total scans
    total_scans = await db.scalar(select(func.count()).select_from(Scan)) or 0

    # Critical findings (total across all scans)
    critical_findings = await db.scalar(
        select(func.count()).select_from(
            select(Finding).where(Finding.severity == FindingSeverity.CRITICAL).subquery()
        )
    ) or 0

    # Compliant apps (apps with at least one completed scan with score >= 80)
    compliant_apps_query = (
        select(func.count(func.distinct(Scan.application_id)))
        .where(Scan.status == ScanStatus.COMPLETED)
        .where(Scan.overall_score >= 80)
    )
    compliant_apps = await db.scalar(compliant_apps_query) or 0

    # Pending scans (running + queued)
    pending_scans = await db.scalar(
        select(func.count()).select_from(
            select(Scan).where(
                Scan.status.in_([ScanStatus.RUNNING, ScanStatus.QUEUED, ScanStatus.PENDING])
            ).subquery()
        )
    ) or 0

    stats = DashboardStats(
        total_scans=total_scans,
        critical_findings=critical_findings,
        compliant_apps=compliant_apps,
        pending_scans=pending_scans,
    )

    # --- Findings by DPDP Section ---

    section_counts = await db.execute(
        select(Finding.dpdp_section, func.count(Finding.id))
        .group_by(Finding.dpdp_section)
        .order_by(func.count(Finding.id).desc())
    )

    # Map section codes to display names
    section_names = {
        "Section 5": "Section 5 - Privacy Notice",
        "Section 6": "Section 6 - Consent",
        "Section 6(6)": "Section 6(6) - Withdrawal",
        "Section 9": "Section 9 - Children's Data",
        "Section 11": "Section 11 - Right to Access",
        "Section 12": "Section 12 - Correction/Erasure",
        "Section 13": "Section 13 - Grievance",
        "Section 14": "Section 14 - Nominate",
        "Dark Patterns": "Dark Patterns",
    }

    findings_by_section = []
    for section, count in section_counts:
        if section:
            display_name = section_names.get(section, section)
            findings_by_section.append(FindingsBySectionItem(
                name=display_name,
                findings=count
            ))

    # If no findings yet, return empty list
    if not findings_by_section:
        findings_by_section = []

    # --- Findings by Severity ---

    severity_counts = await db.execute(
        select(Finding.severity, func.count(Finding.id))
        .group_by(Finding.severity)
    )

    severity_map = {
        FindingSeverity.CRITICAL: "Critical",
        FindingSeverity.HIGH: "High",
        FindingSeverity.MEDIUM: "Medium",
        FindingSeverity.LOW: "Low",
        FindingSeverity.INFO: "Info",
    }

    # Initialize all severities with 0
    severity_data = {
        "Critical": 0,
        "High": 0,
        "Medium": 0,
        "Low": 0,
    }

    for severity, count in severity_counts:
        if severity and severity in severity_map:
            name = severity_map[severity]
            if name in severity_data:
                severity_data[name] = count

    findings_by_severity = [
        FindingsBySeverityItem(name=name, value=value)
        for name, value in severity_data.items()
    ]

    return DashboardData(
        stats=stats,
        findings_by_section=findings_by_section,
        findings_by_severity=findings_by_severity,
    )
