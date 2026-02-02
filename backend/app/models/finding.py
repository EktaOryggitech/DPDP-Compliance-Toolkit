"""
DPDP GUI Compliance Scanner - Finding Model
"""
import enum
from typing import TYPE_CHECKING, List, Optional
import uuid

from sqlalchemy import Enum, ForeignKey, Numeric, String, Text, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.scan import Scan
    from app.models.evidence import Evidence


class FindingSeverity(str, enum.Enum):
    """Severity level of a finding."""
    CRITICAL = "critical"  # ₹250 crore penalty risk
    HIGH = "high"  # ₹200 crore penalty risk
    MEDIUM = "medium"  # ₹50 crore penalty risk
    LOW = "low"  # Best practice deviation
    INFO = "info"  # Informational


class FindingStatus(str, enum.Enum):
    """Status of a finding."""
    PASS = "pass"
    PARTIAL = "partial"
    FAIL = "fail"
    NOT_APPLICABLE = "not_applicable"
    ERROR = "error"


class CheckType(str, enum.Enum):
    """Type of compliance check."""
    # Section 5 - Privacy Notice
    PRIVACY_NOTICE_VISIBILITY = "privacy_notice_visibility"
    PRIVACY_NOTICE_CLARITY = "privacy_notice_clarity"
    PRIVACY_NOTICE_READABILITY = "privacy_notice_readability"
    PRIVACY_NOTICE_MULTILANG = "privacy_notice_multilang"
    PRIVACY_NOTICE_PURPOSE = "privacy_notice_purpose"
    PRIVACY_NOTICE_RIGHTS = "privacy_notice_rights"
    PRIVACY_NOTICE_CONTACT = "privacy_notice_contact"
    PRIVACY_NOTICE_MISSING_LINK = "privacy_notice_missing_link"
    PRIVACY_NOTICE_MISSING_DATA_TYPES = "privacy_notice_missing_data_types"
    PRIVACY_NOTICE_MISSING_PURPOSE = "privacy_notice_missing_purpose"
    PRIVACY_NOTICE_MISSING_FIDUCIARY = "privacy_notice_missing_fiduciary"
    PRIVACY_NOTICE_MISSING_RIGHTS = "privacy_notice_missing_rights"
    PRIVACY_NOTICE_MISSING_GRIEVANCE = "privacy_notice_missing_grievance"
    PRIVACY_NOTICE_INCOMPLETE = "privacy_notice_incomplete"
    PRIVACY_NOTICE_LANGUAGE = "privacy_notice_language"

    # Section 6 - Consent
    CONSENT_CHECKBOX_PRESENT = "consent_checkbox_present"
    CONSENT_NOT_PRESELECTED = "consent_not_preselected"
    CONSENT_GRANULAR = "consent_granular"
    CONSENT_LANGUAGE_CLEAR = "consent_language_clear"

    # Section 6(6) - Withdrawal
    WITHDRAWAL_VISIBLE = "withdrawal_visible"
    WITHDRAWAL_EASY = "withdrawal_easy"
    WITHDRAWAL_ONE_CLICK = "withdrawal_one_click"

    # Section 9 - Children
    CHILDREN_AGE_VERIFICATION = "children_age_verification"
    CHILDREN_PARENTAL_CONSENT = "children_parental_consent"
    CHILDREN_DOB_FIELD = "children_dob_field"

    # Sections 11-14 - Rights
    RIGHTS_ACCESS = "rights_access"
    RIGHTS_CORRECTION = "rights_correction"
    RIGHTS_ERASURE = "rights_erasure"
    RIGHTS_GRIEVANCE = "rights_grievance"
    RIGHTS_NOMINATION = "rights_nomination"

    # Dark Patterns
    DARK_PATTERN_PRESELECTED = "dark_pattern_preselected"
    DARK_PATTERN_CONFIRM_SHAMING = "dark_pattern_confirm_shaming"
    DARK_PATTERN_HIDDEN_OPTION = "dark_pattern_hidden_option"
    DARK_PATTERN_FORCED_ACTION = "dark_pattern_forced_action"
    DARK_PATTERN_MISDIRECTION = "dark_pattern_misdirection"
    DARK_PATTERN_URGENCY = "dark_pattern_urgency"
    DARK_PATTERN_SCARCITY = "dark_pattern_scarcity"
    DARK_PATTERN_DRIP_PRICING = "dark_pattern_drip_pricing"

    # Other
    OTHER = "other"


class Finding(BaseModel):
    """
    Finding model.
    Represents a compliance finding from a scan.
    """

    __tablename__ = "findings"

    # Scan Reference
    scan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("scans.id", ondelete="CASCADE"),
        nullable=False
    )

    # Check Information
    check_type: Mapped[CheckType] = mapped_column(
        Enum(CheckType),
        nullable=False
    )
    dpdp_section: Mapped[Optional[str]] = mapped_column(String(50))  # e.g., "Section 5", "Section 6(6)"

    # Result
    status: Mapped[FindingStatus] = mapped_column(
        Enum(FindingStatus),
        nullable=False
    )
    severity: Mapped[FindingSeverity] = mapped_column(
        Enum(FindingSeverity),
        nullable=False
    )
    confidence: Mapped[Optional[float]] = mapped_column(Numeric(3, 2))  # 0.00 to 1.00

    # Location
    location: Mapped[Optional[str]] = mapped_column(String(2048))  # URL or window title
    element_xpath: Mapped[Optional[str]] = mapped_column(Text)  # For web elements
    element_selector: Mapped[Optional[str]] = mapped_column(Text)  # CSS selector

    # Description
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    remediation: Mapped[Optional[str]] = mapped_column(Text)

    # Additional Data
    extra_data: Mapped[Optional[dict]] = mapped_column(JSON)  # Additional context

    # Screenshot Evidence
    screenshot_path: Mapped[Optional[str]] = mapped_column(Text)  # MinIO storage path for violation screenshot

    # Relationships
    scan: Mapped["Scan"] = relationship("Scan", back_populates="findings")
    evidence: Mapped[List["Evidence"]] = relationship(
        "Evidence",
        back_populates="finding",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Finding(id={self.id}, type={self.check_type}, status={self.status})>"
