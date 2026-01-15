"""
DPDP GUI Compliance Scanner - Base Detector

Abstract base class for all compliance detectors.
"""
from abc import ABC, abstractmethod
from typing import List, Optional

from app.models.finding import Finding
from app.scanners.web.crawler import CrawledPage


class BaseDetector(ABC):
    """
    Abstract base class for compliance detectors.

    All detectors should inherit from this class and implement
    the detect() method.
    """

    # DPDP section this detector covers
    dpdp_section: str = ""

    # Brief description of what this detector checks
    description: str = ""

    def __init__(self):
        pass

    @abstractmethod
    async def detect(self, page: CrawledPage) -> List[Finding]:
        """
        Detect compliance issues on a crawled page.

        Args:
            page: CrawledPage with HTML content and metadata

        Returns:
            List of Finding objects for detected issues
        """
        pass

    def _create_finding(
        self,
        check_type: str,
        severity: str,
        title: str,
        description: str,
        page_url: str,
        element_selector: Optional[str] = None,
        element_html: Optional[str] = None,
        remediation: Optional[str] = None,
    ) -> Finding:
        """Helper to create a Finding object."""
        return Finding(
            check_type=check_type,
            severity=severity,
            title=title,
            description=description,
            page_url=page_url,
            element_selector=element_selector,
            element_html=element_html,
            dpdp_section=self.dpdp_section,
            remediation=remediation,
        )
