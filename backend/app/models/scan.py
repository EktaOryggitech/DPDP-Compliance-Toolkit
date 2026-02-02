"""
DPDP GUI Compliance Scanner - Scan Model
"""
import enum
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
import uuid

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Numeric, String, Text, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.application import Application
    from app.models.finding import Finding


class ScanStatus(str, enum.Enum):
    """Scan execution status."""
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ScanType(str, enum.Enum):
    """Type of scan to perform."""
    QUICK = "quick"  # Fast scan, limited depth
    STANDARD = "standard"  # Balanced scan
    DEEP = "deep"  # Comprehensive scan
    SCHEDULED = "scheduled"  # Scheduled scan (uses standard settings)


class Scan(BaseModel):
    """
    Scan model.
    Represents a compliance scan job.
    """

    __tablename__ = "scans"

    # Application Reference
    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("applications.id", ondelete="CASCADE"),
        nullable=False
    )

    # Scan Configuration
    scan_type: Mapped[ScanType] = mapped_column(
        Enum(ScanType),
        default=ScanType.STANDARD,
        nullable=False
    )

    # Status
    status: Mapped[ScanStatus] = mapped_column(
        Enum(ScanStatus),
        default=ScanStatus.PENDING,
        nullable=False
    )
    status_message: Mapped[Optional[str]] = mapped_column(Text)

    # Progress
    pages_scanned: Mapped[int] = mapped_column(Integer, default=0)
    total_pages: Mapped[Optional[int]] = mapped_column(Integer)
    progress_percentage: Mapped[int] = mapped_column(Integer, default=0)
    current_url: Mapped[Optional[str]] = mapped_column(String(2048))

    # Timing
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Results Summary
    overall_score: Mapped[Optional[float]] = mapped_column(Numeric(5, 2))
    findings_count: Mapped[int] = mapped_column(Integer, default=0)
    critical_count: Mapped[int] = mapped_column(Integer, default=0)
    high_count: Mapped[int] = mapped_column(Integer, default=0)
    medium_count: Mapped[int] = mapped_column(Integer, default=0)
    low_count: Mapped[int] = mapped_column(Integer, default=0)

    # Metadata
    scan_config: Mapped[Optional[dict]] = mapped_column(JSON)  # Configuration used
    scan_metadata: Mapped[Optional[dict]] = mapped_column(JSON)  # Additional metadata

    # Initiated by
    initiated_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # Relationships
    application: Mapped["Application"] = relationship(
        "Application",
        back_populates="scans"
    )
    findings: Mapped[List["Finding"]] = relationship(
        "Finding",
        back_populates="scan",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Scan(id={self.id}, status={self.status}, score={self.overall_score})>"

    @property
    def duration_seconds(self) -> Optional[int]:
        """Calculate scan duration in seconds."""
        if self.started_at and self.completed_at:
            return int((self.completed_at - self.started_at).total_seconds())
        return None
