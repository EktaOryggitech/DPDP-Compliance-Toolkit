"""
DPDP GUI Compliance Scanner - Windows Application Scanner

Orchestrates compliance detection on Windows applications.
"""
import uuid
from dataclasses import dataclass
from typing import Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.finding import CheckType, Finding, FindingSeverity
from app.models.evidence import Evidence, EvidenceType
from app.scanners.windows.controller import WindowInfo, WindowElement


@dataclass
class WindowScanResult:
    """Result of scanning a Windows window."""
    window_title: str
    findings: List[Finding]
    evidence: List[Evidence]
    elements_scanned: int


class WindowsScanner:
    """
    Windows application scanner that runs compliance detectors.

    Uses:
    - pywinauto for UI element extraction
    - OpenCV for screenshot analysis
    - Tesseract for OCR on visual elements
    """

    def __init__(self, scan_id: uuid.UUID, db: AsyncSession):
        self.scan_id = scan_id
        self.db = db
        self._initialize_detectors()

    def _initialize_detectors(self):
        """Initialize all compliance detectors for Windows apps."""
        # TODO: Import Windows-specific detectors
        # from app.detectors.windows.privacy_notice import WindowsPrivacyNoticeDetector
        # from app.detectors.windows.consent import WindowsConsentDetector
        # from app.detectors.windows.dark_patterns import WindowsDarkPatternDetector
        #
        # self.detectors = [
        #     WindowsPrivacyNoticeDetector(),
        #     WindowsConsentDetector(),
        #     WindowsDarkPatternDetector(),
        # ]
        self.detectors = []

    async def scan_window(
        self,
        window: WindowInfo,
        elements: List[WindowElement],
        screenshot_path: Optional[str] = None,
        ocr_text: Optional[str] = None,
    ) -> WindowScanResult:
        """
        Scan a Windows window for compliance issues.

        Args:
            window: WindowInfo with window metadata
            elements: List of UI elements extracted from the window
            screenshot_path: Path to screenshot for evidence
            ocr_text: OCR-extracted text from screenshot

        Returns:
            WindowScanResult with findings and evidence
        """
        findings = []
        evidence = []

        # Combine text from all elements for analysis
        all_text = self._combine_element_text(elements)

        # Add OCR text if available
        if ocr_text:
            all_text += "\n" + ocr_text

        for detector in self.detectors:
            try:
                detector_findings = await detector.detect(
                    window=window,
                    elements=elements,
                    text_content=all_text,
                )

                for finding in detector_findings:
                    finding.scan_id = self.scan_id
                    finding.page_url = f"window://{window.title}"
                    findings.append(finding)
                    self.db.add(finding)

            except Exception as e:
                print(f"Detector {detector.__class__.__name__} failed: {e}")

        await self.db.flush()

        return WindowScanResult(
            window_title=window.title,
            findings=findings,
            evidence=evidence,
            elements_scanned=len(elements),
        )

    def _combine_element_text(self, elements: List[WindowElement]) -> str:
        """Combine text from all UI elements."""
        texts = []
        for el in elements:
            if el.text:
                texts.append(el.text)
            if el.name:
                texts.append(el.name)
        return "\n".join(texts)

    async def analyze_consent_checkboxes(
        self,
        elements: List[WindowElement],
    ) -> List[Finding]:
        """
        Analyze checkbox elements for consent compliance issues.

        Checks:
        - Pre-checked consent checkboxes (dark pattern)
        - Bundled consent (multiple items in one checkbox)
        - Missing granular options
        """
        findings = []

        checkboxes = [el for el in elements if el.control_type == "CheckBox"]

        for cb in checkboxes:
            text = (cb.text + " " + cb.name).lower()

            # Check for consent-related checkboxes
            consent_keywords = ["consent", "agree", "privacy", "data", "terms", "सहमति"]
            is_consent = any(kw in text for kw in consent_keywords)

            if is_consent:
                # Check if pre-checked
                if cb.properties.get("checked", False):
                    finding = Finding(
                        scan_id=self.scan_id,
                        check_type=CheckType.DARK_PATTERN_PRE_CHECKED,
                        severity=FindingSeverity.HIGH,
                        title="Pre-checked consent checkbox detected",
                        description=f"Consent checkbox '{cb.text[:100]}' is pre-checked, which violates DPDP requirements for explicit consent.",
                        page_url=f"element://{cb.automation_id}",
                        element_selector=cb.automation_id,
                        dpdp_section="Section 6",
                        remediation="Ensure consent checkboxes are not pre-checked. Users must actively opt-in.",
                    )
                    findings.append(finding)

                # Check for bundled consent (multiple topics in one checkbox)
                bundled_keywords = [
                    ("marketing", "newsletter"),
                    ("third party", "partner"),
                    ("analytics", "tracking"),
                ]
                for keywords in bundled_keywords:
                    if all(kw in text for kw in keywords):
                        finding = Finding(
                            scan_id=self.scan_id,
                            check_type=CheckType.CONSENT_BUNDLED,
                            severity=FindingSeverity.MEDIUM,
                            title="Bundled consent detected",
                            description=f"Checkbox bundles multiple consent purposes: {cb.text[:100]}",
                            page_url=f"element://{cb.automation_id}",
                            element_selector=cb.automation_id,
                            dpdp_section="Section 6",
                            remediation="Provide separate checkboxes for each consent purpose.",
                        )
                        findings.append(finding)

        return findings

    async def calculate_compliance_score(self) -> Dict:
        """Calculate compliance score for Windows application scan."""
        return {
            "overall_score": 0,
            "sections": {
                "section_5": {"score": 0, "findings_count": 0},
                "section_6": {"score": 0, "findings_count": 0},
                "dark_patterns": {"score": 0, "findings_count": 0},
            },
        }
