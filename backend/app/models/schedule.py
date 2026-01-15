"""
DPDP GUI Compliance Scanner - Schedule Model
"""
import enum
from datetime import datetime, time
from typing import TYPE_CHECKING, Optional
import uuid

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, Time
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.application import Application


class ScheduleFrequency(str, enum.Enum):
    """Frequency of scheduled scans."""
    DAILY = "daily"
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    MONTHLY = "monthly"


class ScanSchedule(BaseModel):
    """
    Scan Schedule model.
    Defines recurring scan schedules for applications.
    """

    __tablename__ = "scan_schedules"

    # Application Reference
    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("applications.id", ondelete="CASCADE"),
        nullable=False
    )

    # Schedule Configuration
    frequency: Mapped[ScheduleFrequency] = mapped_column(
        Enum(ScheduleFrequency),
        nullable=False
    )
    day_of_week: Mapped[Optional[int]] = mapped_column(Integer)  # 0-6 for weekly (Monday=0)
    day_of_month: Mapped[Optional[int]] = mapped_column(Integer)  # 1-28 for monthly
    time_of_day: Mapped[time] = mapped_column(Time, nullable=False)
    timezone: Mapped[str] = mapped_column(default="Asia/Kolkata")

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Tracking
    last_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    next_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    run_count: Mapped[int] = mapped_column(Integer, default=0)

    # Relationships
    application: Mapped["Application"] = relationship(
        "Application",
        back_populates="schedules"
    )

    def __repr__(self) -> str:
        return f"<ScanSchedule(id={self.id}, frequency={self.frequency}, app={self.application_id})>"
