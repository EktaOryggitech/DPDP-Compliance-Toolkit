"""
DPDP GUI Compliance Scanner - Schedules API Routes
"""
from datetime import time
from typing import List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, DbSession
from app.models.application import Application
from app.models.schedule import ScanSchedule, ScheduleFrequency
from app.schemas.common import Message

router = APIRouter()


class ScheduleCreate(BaseModel):
    """Schedule creation schema."""
    application_id: uuid.UUID
    frequency: ScheduleFrequency
    day_of_week: Optional[int] = Field(None, ge=0, le=6)  # Monday=0
    day_of_month: Optional[int] = Field(None, ge=1, le=28)
    time_of_day: time
    timezone: str = "Asia/Kolkata"


class ScheduleUpdate(BaseModel):
    """Schedule update schema."""
    frequency: Optional[ScheduleFrequency] = None
    day_of_week: Optional[int] = Field(None, ge=0, le=6)
    day_of_month: Optional[int] = Field(None, ge=1, le=28)
    time_of_day: Optional[time] = None
    timezone: Optional[str] = None
    is_active: Optional[bool] = None


class ScheduleResponse(BaseModel):
    """Schedule response schema."""
    id: uuid.UUID
    application_id: uuid.UUID
    application_name: Optional[str] = None
    frequency: ScheduleFrequency
    day_of_week: Optional[int]
    day_of_month: Optional[int]
    time_of_day: time
    timezone: str
    is_active: bool
    last_run_at: Optional[str]
    next_run_at: Optional[str]
    run_count: int

    class Config:
        from_attributes = True


@router.get("", response_model=List[ScheduleResponse])
async def list_schedules(
    db: DbSession,
    current_user: CurrentUser,
    application_id: Optional[uuid.UUID] = None,
    is_active: Optional[bool] = None,
):
    """
    List scan schedules.
    """
    query = select(ScanSchedule)

    if application_id:
        query = query.where(ScanSchedule.application_id == application_id)

    if is_active is not None:
        query = query.where(ScanSchedule.is_active == is_active)

    result = await db.execute(query.order_by(ScanSchedule.created_at.desc()))
    schedules = result.scalars().all()

    # Enrich with application names
    items = []
    for schedule in schedules:
        app_result = await db.execute(
            select(Application.name).where(Application.id == schedule.application_id)
        )
        app_name = app_result.scalar_one_or_none()

        response = ScheduleResponse.model_validate(schedule)
        response.application_name = app_name
        items.append(response)

    return items


@router.get("/{schedule_id}", response_model=ScheduleResponse)
async def get_schedule(
    schedule_id: uuid.UUID,
    db: DbSession,
    current_user: CurrentUser,
):
    """
    Get schedule by ID.
    """
    result = await db.execute(
        select(ScanSchedule).where(ScanSchedule.id == schedule_id)
    )
    schedule = result.scalar_one_or_none()

    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Schedule not found",
        )

    return schedule


@router.post("", response_model=ScheduleResponse, status_code=status.HTTP_201_CREATED)
async def create_schedule(
    request: ScheduleCreate,
    db: DbSession,
    current_user: CurrentUser,
):
    """
    Create a new scan schedule.
    """
    # Verify application exists
    app_result = await db.execute(
        select(Application).where(Application.id == request.application_id)
    )
    if not app_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found",
        )

    # Validate schedule parameters
    if request.frequency == ScheduleFrequency.WEEKLY and request.day_of_week is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="day_of_week is required for weekly schedules",
        )

    if request.frequency == ScheduleFrequency.MONTHLY and request.day_of_month is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="day_of_month is required for monthly schedules",
        )

    schedule = ScanSchedule(
        application_id=request.application_id,
        frequency=request.frequency,
        day_of_week=request.day_of_week,
        day_of_month=request.day_of_month,
        time_of_day=request.time_of_day,
        timezone=request.timezone,
    )

    # TODO: Calculate next_run_at

    db.add(schedule)
    await db.commit()
    await db.refresh(schedule)

    return schedule


@router.put("/{schedule_id}", response_model=ScheduleResponse)
async def update_schedule(
    schedule_id: uuid.UUID,
    request: ScheduleUpdate,
    db: DbSession,
    current_user: CurrentUser,
):
    """
    Update a schedule.
    """
    result = await db.execute(
        select(ScanSchedule).where(ScanSchedule.id == schedule_id)
    )
    schedule = result.scalar_one_or_none()

    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Schedule not found",
        )

    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(schedule, field, value)

    # TODO: Recalculate next_run_at if frequency/time changed

    await db.commit()
    await db.refresh(schedule)

    return schedule


@router.delete("/{schedule_id}", response_model=Message)
async def delete_schedule(
    schedule_id: uuid.UUID,
    db: DbSession,
    current_user: CurrentUser,
):
    """
    Delete a schedule.
    """
    result = await db.execute(
        select(ScanSchedule).where(ScanSchedule.id == schedule_id)
    )
    schedule = result.scalar_one_or_none()

    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Schedule not found",
        )

    await db.delete(schedule)
    await db.commit()

    return Message(message="Schedule deleted successfully")
