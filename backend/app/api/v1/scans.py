"""
DPDP GUI Compliance Scanner - Scans API Routes
"""
from typing import List, Optional
import asyncio
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status, WebSocket, WebSocketDisconnect, BackgroundTasks
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, DbSession
from app.core.websocket import manager, websocket_subscriber, ScanProgress as WsScanProgress
from app.core.config import settings
from app.models.application import Application, ApplicationType
from app.models.scan import Scan, ScanStatus, ScanType
from app.models.finding import Finding
from app.schemas.scan import (
    ScanCreate,
    ScanResponse,
    ScanDetailResponse,
    ScanProgress,
    ScanSummary,
)
from app.schemas.common import Message, PaginatedResponse, PaginationParams

router = APIRouter()


@router.get("/summary", response_model=ScanSummary)
async def get_scans_summary(
    db: DbSession,
    current_user: CurrentUser,
    organization_id: Optional[uuid.UUID] = None,
):
    """
    Get scan summary statistics.
    """
    # Base query for scans
    query = select(Scan)

    if organization_id:
        query = query.join(Application).where(Application.organization_id == organization_id)

    # Total scans
    total = await db.scalar(select(func.count()).select_from(query.subquery()))

    # Completed scans
    completed = await db.scalar(
        select(func.count()).select_from(
            query.where(Scan.status == ScanStatus.COMPLETED).subquery()
        )
    )

    # Running scans
    running = await db.scalar(
        select(func.count()).select_from(
            query.where(Scan.status == ScanStatus.RUNNING).subquery()
        )
    )

    # Failed scans
    failed = await db.scalar(
        select(func.count()).select_from(
            query.where(Scan.status == ScanStatus.FAILED).subquery()
        )
    )

    # Average score
    avg_score_result = await db.execute(
        select(func.avg(Scan.overall_score)).where(Scan.status == ScanStatus.COMPLETED)
    )
    avg_score = avg_score_result.scalar()

    # Findings counts
    critical = await db.scalar(select(func.sum(Scan.critical_count))) or 0
    high = await db.scalar(select(func.sum(Scan.high_count))) or 0
    medium = await db.scalar(select(func.sum(Scan.medium_count))) or 0
    low = await db.scalar(select(func.sum(Scan.low_count))) or 0

    return ScanSummary(
        total_scans=total,
        completed_scans=completed,
        running_scans=running,
        failed_scans=failed,
        average_score=float(avg_score) if avg_score else None,
        critical_findings=critical,
        high_findings=high,
        medium_findings=medium,
        low_findings=low,
    )


@router.get("", response_model=PaginatedResponse[ScanResponse])
async def list_scans(
    db: DbSession,
    current_user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    application_id: Optional[uuid.UUID] = None,
    status: Optional[ScanStatus] = None,
    scan_type: Optional[ScanType] = None,
):
    """
    List scans (with pagination and filters).
    """
    query = select(Scan)

    if application_id:
        query = query.where(Scan.application_id == application_id)

    if status:
        query = query.where(Scan.status == status)

    if scan_type:
        query = query.where(Scan.scan_type == scan_type)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)

    # Apply pagination
    query = query.offset((page - 1) * page_size).limit(page_size)
    query = query.order_by(Scan.created_at.desc())

    result = await db.execute(query)
    scans = result.scalars().all()

    # Enrich with application names
    items = []
    for scan in scans:
        app_result = await db.execute(
            select(Application.name).where(Application.id == scan.application_id)
        )
        app_name = app_result.scalar_one_or_none()

        scan_response = ScanResponse.model_validate(scan)
        scan_response.application_name = app_name
        scan_response.duration_seconds = scan.duration_seconds

        items.append(scan_response)

    return PaginatedResponse.create(
        items=items,
        total=total,
        params=PaginationParams(page=page, page_size=page_size),
    )


@router.get("/{scan_id}", response_model=ScanDetailResponse)
async def get_scan(
    scan_id: uuid.UUID,
    db: DbSession,
    current_user: CurrentUser,
):
    """
    Get scan details by ID.
    """
    result = await db.execute(select(Scan).where(Scan.id == scan_id))
    scan = result.scalar_one_or_none()

    if not scan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scan not found",
        )

    # Get application name
    app_result = await db.execute(
        select(Application.name).where(Application.id == scan.application_id)
    )
    app_name = app_result.scalar_one_or_none()

    # Get findings breakdown
    findings_by_section = {}
    findings_by_type = {}

    findings_result = await db.execute(
        select(Finding).where(Finding.scan_id == scan_id)
    )
    findings = findings_result.scalars().all()

    for finding in findings:
        # By section
        section = finding.dpdp_section or "Other"
        findings_by_section[section] = findings_by_section.get(section, 0) + 1

        # By type
        check_type = finding.check_type.value
        findings_by_type[check_type] = findings_by_type.get(check_type, 0) + 1

    response = ScanDetailResponse.model_validate(scan)
    response.application_name = app_name
    response.duration_seconds = scan.duration_seconds
    response.findings_by_section = findings_by_section
    response.findings_by_type = findings_by_type

    return response


@router.post("", response_model=ScanResponse, status_code=status.HTTP_201_CREATED)
async def create_scan(
    request: ScanCreate,
    db: DbSession,
    current_user: CurrentUser,
):
    """
    Create and start a new scan.
    """
    # Verify application exists
    app_result = await db.execute(
        select(Application).where(Application.id == request.application_id)
    )
    application = app_result.scalar_one_or_none()

    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found",
        )

    # Check if there's already a running scan
    running_scan = await db.execute(
        select(Scan)
        .where(Scan.application_id == request.application_id)
        .where(Scan.status.in_([ScanStatus.PENDING, ScanStatus.QUEUED, ScanStatus.RUNNING]))
    )
    if running_scan.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A scan is already in progress for this application",
        )

    # Create scan
    scan = Scan(
        application_id=request.application_id,
        scan_type=request.scan_type,
        status=ScanStatus.QUEUED,
        initiated_by=current_user.id,
        scan_config=request.config_overrides or application.scan_config,
    )

    db.add(scan)
    await db.commit()
    await db.refresh(scan)

    # Queue scan task with Celery
    from app.workers.tasks.scan_tasks import run_web_scan, run_windows_scan

    if application.app_type == ApplicationType.WEB:
        run_web_scan.delay(str(scan.id), str(application.id))
    else:
        run_windows_scan.delay(str(scan.id), str(application.id))

    return scan


@router.post("/{scan_id}/cancel", response_model=Message)
async def cancel_scan(
    scan_id: uuid.UUID,
    db: DbSession,
    current_user: CurrentUser,
):
    """
    Cancel a running scan.
    """
    result = await db.execute(select(Scan).where(Scan.id == scan_id))
    scan = result.scalar_one_or_none()

    if not scan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scan not found",
        )

    if scan.status not in [ScanStatus.PENDING, ScanStatus.QUEUED, ScanStatus.RUNNING]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Scan cannot be cancelled in current status",
        )

    scan.status = ScanStatus.CANCELLED
    scan.status_message = "Cancelled by user"
    await db.commit()

    return Message(message="Scan cancelled successfully")


@router.websocket("/ws/{scan_id}")
async def scan_progress_websocket(
    websocket: WebSocket,
    scan_id: uuid.UUID,
):
    """
    WebSocket endpoint for real-time scan progress updates.

    Clients connect to receive:
    - progress: Periodic updates on scan progress
    - finding: New finding detected
    - completed: Scan finished
    - error: Error occurred
    """
    await manager.connect(websocket, str(scan_id))

    # Start Redis subscriber for this scan
    subscriber_task = asyncio.create_task(
        websocket_subscriber(str(scan_id), settings.REDIS_URL)
    )

    try:
        while True:
            # Keep connection alive by waiting for client messages
            # (ping/pong or control messages)
            data = await websocket.receive_text()

            # Handle client commands if any
            if data == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        pass
    finally:
        subscriber_task.cancel()
        await manager.disconnect(websocket)


@router.get("/{scan_id}/progress", response_model=ScanProgress)
async def get_scan_progress(
    scan_id: uuid.UUID,
    db: DbSession,
    current_user: CurrentUser,
):
    """
    Get current scan progress (for polling fallback).
    """
    result = await db.execute(select(Scan).where(Scan.id == scan_id))
    scan = result.scalar_one_or_none()

    if not scan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scan not found",
        )

    # Calculate progress percentage
    if scan.status == ScanStatus.COMPLETED:
        percent = 100
    elif scan.status == ScanStatus.RUNNING:
        # Estimate based on pages scanned vs expected
        max_pages = 100  # Could be from config
        percent = min(int((scan.pages_scanned / max_pages) * 100), 99)
    elif scan.status in [ScanStatus.PENDING, ScanStatus.QUEUED]:
        percent = 0
    else:
        percent = 100  # Failed/cancelled

    return ScanProgress(
        scan_id=scan_id,
        status=scan.status.value,
        percent=percent,
        pages_scanned=scan.pages_scanned,
        findings_count=scan.findings_count,
        current_url=None,
        message=scan.status_message or f"Status: {scan.status.value}",
    )


async def broadcast_scan_progress(scan_id: uuid.UUID, progress: ScanProgress):
    """
    Broadcast scan progress to all connected WebSocket clients.
    Called by scan worker via Redis pub/sub.
    """
    ws_progress = WsScanProgress(
        scan_id=str(scan_id),
        status=progress.status,
        current_step=progress.percent,
        total_steps=100,
        percent=progress.percent,
        message=progress.message,
        current_url=progress.current_url,
        findings_count=progress.findings_count,
        pages_scanned=progress.pages_scanned,
    )
    await manager.send_progress(ws_progress)
