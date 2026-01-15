"""
DPDP GUI Compliance Scanner - Evidence Model
"""
import enum
from typing import TYPE_CHECKING, Optional
import uuid

from sqlalchemy import Enum, ForeignKey, String, Text, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.finding import Finding


class EvidenceType(str, enum.Enum):
    """Type of evidence captured."""
    SCREENSHOT_FULL = "screenshot_full"
    SCREENSHOT_ELEMENT = "screenshot_element"
    HTML_SNIPPET = "html_snippet"
    TEXT_CONTENT = "text_content"
    DOM_TREE = "dom_tree"
    NETWORK_HAR = "network_har"


class Evidence(BaseModel):
    """
    Evidence model.
    Stores evidence for findings (screenshots, HTML snippets, etc.).
    """

    __tablename__ = "evidence"

    # Finding Reference
    finding_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("findings.id", ondelete="CASCADE"),
        nullable=False
    )

    # Evidence Type
    type: Mapped[EvidenceType] = mapped_column(
        Enum(EvidenceType),
        nullable=False
    )

    # Storage
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)  # MinIO path
    file_name: Mapped[Optional[str]] = mapped_column(String(255))
    mime_type: Mapped[Optional[str]] = mapped_column(String(100))
    file_size: Mapped[Optional[int]] = mapped_column()

    # Annotations (for screenshots)
    annotations: Mapped[Optional[dict]] = mapped_column(JSON)  # Highlight regions, labels

    # Text content (for snippets)
    text_content: Mapped[Optional[str]] = mapped_column(Text)

    # Extra Data
    extra_data: Mapped[Optional[dict]] = mapped_column(JSON)

    # Relationships
    finding: Mapped["Finding"] = relationship("Finding", back_populates="evidence")

    def __repr__(self) -> str:
        return f"<Evidence(id={self.id}, type={self.type}, finding_id={self.finding_id})>"
