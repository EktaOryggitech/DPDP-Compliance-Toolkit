"""
DPDP GUI Compliance Scanner - Schedules API Routes
"""
from datetime import datetime, time, timedelta
from typing import List, Optional
import uuid
import pytz

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, DbSession
from app.models.application import Application
from app.models.schedule import ScanSchedule, ScheduleFrequency
from app.schemas.common import Message


def calculate_next_run(frequency: ScheduleFrequency, time_of_day: time, timezone: str,
                       day_of_week: Optional[int] = None, day_of_month: Optional[int] = None) -> datetime:
    """Calculate the next run time based on schedule configuration."""
    try:
        tz = pytz.timezone(timezone)
    except:
        tz = pytz.timezone("Asia/Kolkata")

    now = datetime.now(tz)

    # Create a datetime for today at the scheduled time
    scheduled_time = tz.localize(datetime.combine(now.date(), time_of_day))

    if frequency == ScheduleFrequency.DAILY:
        # If today's time has passed, schedule for tomorrow
        if scheduled_time <= now:
            scheduled_time += timedelta(days=1)
        return scheduled_time.astimezone(pytz.UTC).replace(tzinfo=None)

    elif frequency == ScheduleFrequency.WEEKLY:
        # day_of_week: 0=Monday, 6=Sunday
        days_ahead = day_of_week - now.weekday()
        if days_ahead < 0 or (days_ahead == 0 and scheduled_time <= now):
            days_ahead += 7
        scheduled_time = tz.localize(datetime.combine(now.date() + timedelta(days=days_ahead), time_of_day))
        return scheduled_time.astimezone(pytz.UTC).replace(tzinfo=None)

    elif frequency == ScheduleFrequency.BIWEEKLY:
        days_ahead = day_of_week - now.weekday() if day_of_week else 0
        if days_ahead < 0 or (days_ahead == 0 and scheduled_time <= now):
            days_ahead += 14
        scheduled_time = tz.localize(datetime.combine(now.date() + timedelta(days=days_ahead), time_of_day))
        return scheduled_time.astimezone(pytz.UTC).replace(tzinfo=None)

    elif frequency == ScheduleFrequency.MONTHLY:
        # Find next occurrence of day_of_month
        target_day = day_of_month or 1
        next_month = now.replace(day=1) + timedelta(days=32)
        next_month = next_month.replace(day=1)

        try:
            scheduled_time = tz.localize(datetime.combine(now.replace(day=target_day), time_of_day))
            if scheduled_time <= now:
                # Schedule for next month
                scheduled_time = tz.localize(datetime.combine(next_month.replace(day=target_day), time_of_day))
        except ValueError:
            # Day doesn't exist in this month (e.g., Feb 30)
            scheduled_time = tz.localize(datetime.combine(next_month.replace(day=target_day), time_of_day))

        return scheduled_time.astimezone(pytz.UTC).replace(tzinfo=None)

    # Default: tomorrow at scheduled time
    return (scheduled_time + timedelta(days=1)).astimezone(pytz.UTC).replace(tzinfo=None)

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
    last_run_at: Optional[datetime] = None
    next_run_at: Optional[datetime] = None
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

    # Calculate next run time
    next_run = calculate_next_run(
        frequency=request.frequency,
        time_of_day=request.time_of_day,
        timezone=request.timezone,
        day_of_week=request.day_of_week,
        day_of_month=request.day_of_month,
    )

    schedule = ScanSchedule(
        application_id=request.application_id,
        frequency=request.frequency,
        day_of_week=request.day_of_week,
        day_of_month=request.day_of_month,
        time_of_day=request.time_of_day,
        timezone=request.timezone,
        next_run_at=next_run,
    )

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

    # Recalculate next_run_at if schedule parameters changed
    if any(key in update_data for key in ['frequency', 'time_of_day', 'day_of_week', 'day_of_month', 'timezone']):
        schedule.next_run_at = calculate_next_run(
            frequency=schedule.frequency,
            time_of_day=schedule.time_of_day,
            timezone=schedule.timezone,
            day_of_week=schedule.day_of_week,
            day_of_month=schedule.day_of_month,
        )

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
