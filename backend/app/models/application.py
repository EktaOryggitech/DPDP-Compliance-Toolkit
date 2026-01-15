"""
DPDP GUI Compliance Scanner - Application Model
"""
import enum
from typing import TYPE_CHECKING, List, Optional
import uuid

from sqlalchemy import Enum, ForeignKey, String, Text, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.scan import Scan
    from app.models.schedule import ScanSchedule


class ApplicationType(str, enum.Enum):
    """Type of application to scan."""
    WEB = "web"
    WINDOWS = "windows"


class Application(BaseModel):
    """
    Application model.
    Represents a web or Windows application to be scanned.
    """

    __tablename__ = "applications"

    # Basic Information
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    type: Mapped[ApplicationType] = mapped_column(
        Enum(ApplicationType),
        nullable=False
    )

    # Web Application Fields
    url: Mapped[Optional[str]] = mapped_column(String(2048))

    # Windows Application Fields
    executable_path: Mapped[Optional[str]] = mapped_column(Text)
    window_title: Mapped[Optional[str]] = mapped_column(String(255))

    # Organization
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False
    )

    # Configuration
    auth_config: Mapped[Optional[dict]] = mapped_column(JSON)  # Authentication settings
    scan_config: Mapped[Optional[dict]] = mapped_column(JSON)  # Scan settings (depth, timeout, etc.)

    # Tags for categorization
    tags: Mapped[Optional[List[str]]] = mapped_column(JSON, default=list)

    # Status
    is_active: Mapped[bool] = mapped_column(default=True)

    # Relationships
    organization: Mapped["Organization"] = relationship(
        "Organization",
        back_populates="applications"
    )
    scans: Mapped[List["Scan"]] = relationship(
        "Scan",
        back_populates="application",
        cascade="all, delete-orphan"
    )
    schedules: Mapped[List["ScanSchedule"]] = relationship(
        "ScanSchedule",
        back_populates="application",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Application(id={self.id}, name='{self.name}', type={self.type})>"
