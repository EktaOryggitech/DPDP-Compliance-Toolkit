"""
DPDP GUI Compliance Scanner - Applications API Routes
"""
from typing import List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, DbSession, require_role
from app.models.application import Application, ApplicationType
from app.models.organization import Organization
from app.models.scan import Scan, ScanStatus
from app.models.user import UserRole
from app.schemas.application import (
    ApplicationCreate,
    ApplicationUpdate,
    ApplicationResponse,
)
from app.schemas.common import Message, PaginatedResponse, PaginationParams

router = APIRouter()


@router.get("", response_model=PaginatedResponse[ApplicationResponse])
async def list_applications(
    db: DbSession,
    current_user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    organization_id: Optional[uuid.UUID] = None,
    app_type: Optional[ApplicationType] = None,
    search: Optional[str] = None,
    is_active: Optional[bool] = None,
):
    """
    List applications (with pagination and filters).
    """
    query = select(Application)

    if organization_id:
        query = query.where(Application.organization_id == organization_id)

    if app_type:
        query = query.where(Application.type == app_type)

    if search:
        query = query.where(Application.name.ilike(f"%{search}%"))

    if is_active is not None:
        query = query.where(Application.is_active == is_active)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)

    # Apply pagination
    query = query.offset((page - 1) * page_size).limit(page_size)
    query = query.order_by(Application.name)

    result = await db.execute(query)
    applications = result.scalars().all()

    # Enrich with scan info
    items = []
    for app in applications:
        # Get last scan
        last_scan_query = (
            select(Scan)
            .where(Scan.application_id == app.id)
            .where(Scan.status == ScanStatus.COMPLETED)
            .order_by(Scan.completed_at.desc())
            .limit(1)
        )
        last_scan_result = await db.execute(last_scan_query)
        last_scan = last_scan_result.scalar_one_or_none()

        # Get scan count
        scan_count = await db.scalar(
            select(func.count()).where(Scan.application_id == app.id)
        )

        app_response = ApplicationResponse.model_validate(app)
        app_response.scans_count = scan_count
        if last_scan:
            app_response.last_scan_at = last_scan.completed_at
            app_response.last_scan_score = float(last_scan.overall_score) if last_scan.overall_score else None

        items.append(app_response)

    return PaginatedResponse.create(
        items=items,
        total=total,
        params=PaginationParams(page=page, page_size=page_size),
    )


@router.get("/{application_id}", response_model=ApplicationResponse)
async def get_application(
    application_id: uuid.UUID,
    db: DbSession,
    current_user: CurrentUser,
):
    """
    Get application by ID.
    """
    result = await db.execute(
        select(Application).where(Application.id == application_id)
    )
    application = result.scalar_one_or_none()

    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found",
        )

    return application


@router.post("", response_model=ApplicationResponse, status_code=status.HTTP_201_CREATED)
async def create_application(
    request: ApplicationCreate,
    db: DbSession,
    current_user: CurrentUser,
):
    """
    Create a new application.
    """
    # Verify organization exists
    org_result = await db.execute(
        select(Organization).where(Organization.id == request.organization_id)
    )
    if not org_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    # Validate based on type
    if request.type == ApplicationType.WEB and not request.url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="URL is required for web applications",
        )

    if request.type == ApplicationType.WINDOWS and not request.executable_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Executable path is required for Windows applications",
        )

    application = Application(
        name=request.name,
        description=request.description,
        type=request.type,
        url=request.url,
        executable_path=request.executable_path,
        window_title=request.window_title,
        organization_id=request.organization_id,
        auth_config=request.auth_config.model_dump() if request.auth_config else None,
        scan_config=request.scan_config.model_dump() if request.scan_config else None,
        tags=request.tags,
    )

    db.add(application)
    await db.commit()
    await db.refresh(application)

    return application


@router.put("/{application_id}", response_model=ApplicationResponse)
async def update_application(
    application_id: uuid.UUID,
    request: ApplicationUpdate,
    db: DbSession,
    current_user: CurrentUser,
):
    """
    Update application.
    """
    result = await db.execute(
        select(Application).where(Application.id == application_id)
    )
    application = result.scalar_one_or_none()

    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found",
        )

    # Update fields
    update_data = request.model_dump(exclude_unset=True)

    # Handle nested configs
    if "auth_config" in update_data and update_data["auth_config"]:
        update_data["auth_config"] = update_data["auth_config"].model_dump() if hasattr(update_data["auth_config"], 'model_dump') else update_data["auth_config"]

    if "scan_config" in update_data and update_data["scan_config"]:
        update_data["scan_config"] = update_data["scan_config"].model_dump() if hasattr(update_data["scan_config"], 'model_dump') else update_data["scan_config"]

    for field, value in update_data.items():
        setattr(application, field, value)

    await db.commit()
    await db.refresh(application)

    return application


@router.delete("/{application_id}", response_model=Message)
async def delete_application(
    application_id: uuid.UUID,
    db: DbSession,
    current_user: CurrentUser,
):
    """
    Delete application.
    """
    result = await db.execute(
        select(Application).where(Application.id == application_id)
    )
    application = result.scalar_one_or_none()

    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found",
        )

    await db.delete(application)
    await db.commit()

    return Message(message="Application deleted successfully")
