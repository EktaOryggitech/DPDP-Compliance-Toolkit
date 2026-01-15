"""
DPDP GUI Compliance Scanner - Organization Model
"""
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.application import Application
    from app.models.user import User


class Organization(BaseModel):
    """
    Organization/Ministry model.
    Represents government ministries, departments, or agencies being audited.
    """

    __tablename__ = "organizations"

    # Basic Information
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[Optional[str]] = mapped_column(String(50), unique=True)
    type: Mapped[Optional[str]] = mapped_column(String(50))  # ministry, department, agency, etc.
    description: Mapped[Optional[str]] = mapped_column(Text)

    # Contact Information
    address: Mapped[Optional[str]] = mapped_column(Text)
    website: Mapped[Optional[str]] = mapped_column(String(255))
    contact_email: Mapped[Optional[str]] = mapped_column(String(255))
    contact_phone: Mapped[Optional[str]] = mapped_column(String(20))

    # Data Protection Officer
    dpo_name: Mapped[Optional[str]] = mapped_column(String(255))
    dpo_email: Mapped[Optional[str]] = mapped_column(String(255))
    dpo_phone: Mapped[Optional[str]] = mapped_column(String(20))

    # Status
    is_active: Mapped[bool] = mapped_column(default=True)

    # Relationships
    applications: Mapped[List["Application"]] = relationship(
        "Application",
        back_populates="organization",
        cascade="all, delete-orphan"
    )
    users: Mapped[List["User"]] = relationship(
        "User",
        back_populates="organization",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Organization(id={self.id}, name='{self.name}')>"
