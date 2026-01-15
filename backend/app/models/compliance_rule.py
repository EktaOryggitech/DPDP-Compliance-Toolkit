"""
DPDP GUI Compliance Scanner - Compliance Rule Model
"""
from typing import Optional

from sqlalchemy import Boolean, Numeric, String, Text, JSON

from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class ComplianceRule(BaseModel):
    """
    Compliance Rule model.
    Defines DPDP compliance rules and their detection logic.
    """

    __tablename__ = "compliance_rules"

    # Rule Identification
    rule_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    dpdp_section: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Description
    description: Mapped[Optional[str]] = mapped_column(Text)
    legal_text: Mapped[Optional[str]] = mapped_column(Text)  # Actual DPDP text

    # Severity and Scoring
    severity: Mapped[str] = mapped_column(String(20), nullable=False)  # critical, high, medium, low
    weight: Mapped[float] = mapped_column(Numeric(3, 2), default=1.0)  # For scoring calculation
    penalty_amount: Mapped[Optional[str]] = mapped_column(String(50))  # e.g., "₹250 crore"

    # Detection Configuration
    check_type: Mapped[str] = mapped_column(String(100), nullable=False)
    detection_logic: Mapped[Optional[dict]] = mapped_column(JSON)  # Rule configuration
    keywords: Mapped[Optional[list]] = mapped_column(JSON)  # Keywords to search for
    patterns: Mapped[Optional[list]] = mapped_column(JSON)  # Regex patterns

    # Remediation
    remediation_template: Mapped[Optional[str]] = mapped_column(Text)
    remediation_priority: Mapped[Optional[int]] = mapped_column()

    # Applicability
    applies_to_web: Mapped[bool] = mapped_column(Boolean, default=True)
    applies_to_windows: Mapped[bool] = mapped_column(Boolean, default=True)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    def __repr__(self) -> str:
        return f"<ComplianceRule(code={self.rule_code}, section={self.dpdp_section})>"
