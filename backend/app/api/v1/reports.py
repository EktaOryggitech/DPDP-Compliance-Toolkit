"""
DPDP GUI Compliance Scanner - Reports API Routes

Provides endpoints for generating and downloading compliance reports.
"""
from typing import Optional
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, DbSession
from app.models.scan import Scan, ScanStatus
from app.models.application import Application
from app.models.finding import Finding
from app.schemas.common import Message
from app.reports import PDFReportGenerator, ExcelReportGenerator
from app.evidence.storage import EvidenceStorage
from app.core.config import settings

router = APIRouter()


@router.get("/{scan_id}/pdf")
async def download_pdf_report(
    scan_id: uuid.UUID,
    db: DbSession,
    current_user: CurrentUser,
    include_evidence: bool = Query(True, description="Include screenshot evidence in report"),
):
    """
    Generate and download PDF compliance report for a scan.

    The PDF includes:
    - Cover page with scan summary
    - Executive summary with compliance score
    - Detailed findings by DPDP section
    - Remediation recommendations
    - Optional screenshot evidence
    """
    # Verify scan exists and is completed
    result = await db.execute(select(Scan).where(Scan.id == scan_id))
    scan = result.scalar_one_or_none()

    if not scan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scan not found",
        )

    if scan.status != ScanStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Report can only be generated for completed scans",
        )

    # Get application details
    app_result = await db.execute(
        select(Application).where(Application.id == scan.application_id)
    )
    application = app_result.scalar_one_or_none()

    # Get findings
    findings_result = await db.execute(
        select(Finding).where(Finding.scan_id == scan_id)
    )
    findings = findings_result.scalars().all()

    # Generate PDF report
    generator = PDFReportGenerator(
        scan=scan,
        application=application,
        findings=list(findings),
        include_evidence=include_evidence,
    )
    pdf_buffer = await generator.generate()

    # Generate filename
    app_name = application.name.replace(" ", "_") if application else "unknown"
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"DPDP_Compliance_Report_{app_name}_{timestamp}.pdf"

    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-cache",
        }
    )


@router.get("/{scan_id}/excel")
async def download_excel_report(
    scan_id: uuid.UUID,
    db: DbSession,
    current_user: CurrentUser,
    include_raw_data: bool = Query(True, description="Include raw findings data sheet"),
):
    """
    Generate and download Excel compliance report for a scan.

    The Excel workbook includes:
    - Summary sheet with overall metrics
    - Findings sheet with all compliance issues
    - Remediation sheet with prioritized action items
    - DPDP Section breakdown
    - Optional raw data for further analysis
    """
    # Verify scan exists and is completed
    result = await db.execute(select(Scan).where(Scan.id == scan_id))
    scan = result.scalar_one_or_none()

    if not scan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scan not found",
        )

    if scan.status != ScanStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Report can only be generated for completed scans",
        )

    # Get application details
    app_result = await db.execute(
        select(Application).where(Application.id == scan.application_id)
    )
    application = app_result.scalar_one_or_none()

    # Get findings
    findings_result = await db.execute(
        select(Finding).where(Finding.scan_id == scan_id)
    )
    findings = findings_result.scalars().all()

    # Generate Excel report
    generator = ExcelReportGenerator(
        scan=scan,
        application=application,
        findings=list(findings),
        include_raw_data=include_raw_data,
    )
    excel_buffer = await generator.generate()

    # Generate filename
    app_name = application.name.replace(" ", "_") if application else "unknown"
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"DPDP_Compliance_Report_{app_name}_{timestamp}.xlsx"

    return StreamingResponse(
        excel_buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-cache",
        }
    )


@router.get("/{scan_id}/evidence/{finding_id}")
async def download_evidence(
    scan_id: uuid.UUID,
    finding_id: uuid.UUID,
    db: DbSession,
    current_user: CurrentUser,
):
    """
    Get presigned URL for evidence file (screenshot, HTML snippet, etc.).

    Returns a temporary URL that can be used to download the evidence file
    directly from object storage.
    """
    # Verify scan exists
    scan_result = await db.execute(select(Scan).where(Scan.id == scan_id))
    scan = scan_result.scalar_one_or_none()

    if not scan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scan not found",
        )

    # Verify finding exists and belongs to scan
    finding_result = await db.execute(
        select(Finding).where(Finding.id == finding_id, Finding.scan_id == scan_id)
    )
    finding = finding_result.scalar_one_or_none()

    if not finding:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Finding not found",
        )

    # Check if evidence exists
    if not finding.screenshot_path and not finding.evidence_html:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No evidence available for this finding",
        )

    # If screenshot is stored in object storage
    if finding.screenshot_path:
        storage = EvidenceStorage(
            endpoint=settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            bucket=settings.MINIO_BUCKET_NAME,
        )

        try:
            presigned_url = await storage.get_presigned_url(
                object_path=finding.screenshot_path,
                expires_hours=1,
            )
            return RedirectResponse(url=presigned_url)

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to retrieve evidence: {str(e)}",
            )

    # If only HTML evidence is available, return as text
    if finding.evidence_html:
        return StreamingResponse(
            iter([finding.evidence_html.encode()]),
            media_type="text/html",
            headers={
                "Content-Disposition": f'attachment; filename="evidence_{finding_id}.html"',
            }
        )


@router.get("/{scan_id}/evidence")
async def list_evidence(
    scan_id: uuid.UUID,
    db: DbSession,
    current_user: CurrentUser,
):
    """
    List all evidence files for a scan.
    """
    # Verify scan exists
    scan_result = await db.execute(select(Scan).where(Scan.id == scan_id))
    scan = scan_result.scalar_one_or_none()

    if not scan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scan not found",
        )

    # Get findings with evidence
    findings_result = await db.execute(
        select(Finding).where(
            Finding.scan_id == scan_id,
            (Finding.screenshot_path.isnot(None)) | (Finding.evidence_html.isnot(None))
        )
    )
    findings = findings_result.scalars().all()

    evidence_list = []
    for finding in findings:
        evidence_list.append({
            "finding_id": str(finding.id),
            "title": finding.title,
            "severity": finding.severity.value if hasattr(finding.severity, 'value') else finding.severity,
            "has_screenshot": finding.screenshot_path is not None,
            "has_html": finding.evidence_html is not None,
            "url": finding.url,
        })

    return {
        "scan_id": str(scan_id),
        "evidence_count": len(evidence_list),
        "evidence": evidence_list,
    }
