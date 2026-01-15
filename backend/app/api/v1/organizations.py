"""
DPDP GUI Compliance Scanner - Organizations API Routes
"""
from typing import List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, DbSession, require_role
from app.models.organization import Organization
from app.models.application import Application
from app.models.user import UserRole
from app.schemas.organization import (
    OrganizationCreate,
    OrganizationUpdate,
    OrganizationResponse,
)
from app.schemas.common import Message, PaginatedResponse, PaginationParams

router = APIRouter()


@router.get("", response_model=PaginatedResponse[OrganizationResponse])
async def list_organizations(
    db: DbSession,
    current_user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    is_active: Optional[bool] = None,
):
    """
    List all organizations (with pagination).
    """
    # Build query
    query = select(Organization)

    if search:
        query = query.where(Organization.name.ilike(f"%{search}%"))

    if is_active is not None:
        query = query.where(Organization.is_active == is_active)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)

    # Apply pagination
    query = query.offset((page - 1) * page_size).limit(page_size)
    query = query.order_by(Organization.name)

    result = await db.execute(query)
    organizations = result.scalars().all()

    # Get application counts
    items = []
    for org in organizations:
        app_count = await db.scalar(
            select(func.count()).where(Application.organization_id == org.id)
        )
        org_dict = OrganizationResponse.model_validate(org).model_dump()
        org_dict["applications_count"] = app_count
        items.append(OrganizationResponse(**org_dict))

    return PaginatedResponse.create(
        items=items,
        total=total,
        params=PaginationParams(page=page, page_size=page_size),
    )


@router.get("/{organization_id}", response_model=OrganizationResponse)
async def get_organization(
    organization_id: uuid.UUID,
    db: DbSession,
    current_user: CurrentUser,
):
    """
    Get organization by ID.
    """
    result = await db.execute(
        select(Organization).where(Organization.id == organization_id)
    )
    organization = result.scalar_one_or_none()

    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    # Get application count
    app_count = await db.scalar(
        select(func.count()).where(Application.organization_id == organization.id)
    )

    response = OrganizationResponse.model_validate(organization)
    response.applications_count = app_count

    return response


@router.post(
    "",
    response_model=OrganizationResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
async def create_organization(
    request: OrganizationCreate,
    db: DbSession,
    current_user: CurrentUser,
):
    """
    Create a new organization. (Admin only)
    """
    # Check for duplicate code
    if request.code:
        result = await db.execute(
            select(Organization).where(Organization.code == request.code)
        )
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Organization code already exists",
            )

    organization = Organization(**request.model_dump())
    db.add(organization)
    await db.commit()
    await db.refresh(organization)

    return organization


@router.put(
    "/{organization_id}",
    response_model=OrganizationResponse,
    dependencies=[Depends(require_role(UserRole.ADMIN, UserRole.AUDITOR))],
)
async def update_organization(
    organization_id: uuid.UUID,
    request: OrganizationUpdate,
    db: DbSession,
    current_user: CurrentUser,
):
    """
    Update organization. (Admin or Auditor)
    """
    result = await db.execute(
        select(Organization).where(Organization.id == organization_id)
    )
    organization = result.scalar_one_or_none()

    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    # Update fields
    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(organization, field, value)

    await db.commit()
    await db.refresh(organization)

    return organization


@router.delete(
    "/{organization_id}",
    response_model=Message,
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
async def delete_organization(
    organization_id: uuid.UUID,
    db: DbSession,
    current_user: CurrentUser,
):
    """
    Delete organization. (Admin only)
    """
    result = await db.execute(
        select(Organization).where(Organization.id == organization_id)
    )
    organization = result.scalar_one_or_none()

    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    await db.delete(organization)
    await db.commit()

    return Message(message="Organization deleted successfully")
