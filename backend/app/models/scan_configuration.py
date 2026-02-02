"""
DPDP GUI Compliance Scanner - Scan Configuration Model

Global configuration for scan type page counts.
"""
from sqlalchemy import Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class ScanConfiguration(BaseModel):
    """
    Global scan configuration.

    Stores admin-configured page counts for each scan type.
    This is a singleton table (only one row should exist).
    """
    __tablename__ = "scan_configurations"

    # Quick scan: 10-50 pages, default 20
    quick_pages: Mapped[int] = mapped_column(
        Integer,
        default=20,
        nullable=False
    )

    # Standard scan: 50-150 pages, default 75
    standard_pages: Mapped[int] = mapped_column(
        Integer,
        default=75,
        nullable=False
    )

    # Deep scan: 150-500 pages, default 200
    deep_pages: Mapped[int] = mapped_column(
        Integer,
        default=200,
        nullable=False
    )

    def __repr__(self) -> str:
        return f"<ScanConfiguration quick={self.quick_pages}, standard={self.standard_pages}, deep={self.deep_pages}>"
