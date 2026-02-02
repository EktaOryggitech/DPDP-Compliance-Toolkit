"""
DPDP GUI Compliance Scanner - Base Detector

Abstract base class for all compliance detectors.
"""
from abc import ABC, abstractmethod
from typing import List, Optional, TYPE_CHECKING

from app.models.finding import Finding
from app.scanners.web.crawler import CrawledPage

if TYPE_CHECKING:
    from bs4 import Tag


def generate_css_selector(element: "Tag") -> Optional[str]:
    """
    Generate a CSS selector for a BeautifulSoup element.

    Tries to create a unique, valid CSS selector that Playwright can use.

    Args:
        element: BeautifulSoup Tag element

    Returns:
        CSS selector string or None if cannot generate
    """
    if element is None:
        return None

    try:
        tag_name = element.name
        if not tag_name:
            return None

        # Priority 1: Use ID if available (most reliable)
        elem_id = element.get("id")
        if elem_id and isinstance(elem_id, str) and elem_id.strip():
            # Escape special characters in ID
            safe_id = elem_id.strip().replace(":", "\\:")
            return f"#{safe_id}"

        # Priority 2: Use name attribute for form elements
        elem_name = element.get("name")
        if elem_name and isinstance(elem_name, str) and elem_name.strip():
            return f'{tag_name}[name="{elem_name.strip()}"]'

        # Priority 3: Build selector with tag + attributes
        selector_parts = [tag_name]

        # Add type attribute for inputs
        elem_type = element.get("type")
        if elem_type and isinstance(elem_type, str):
            selector_parts.append(f'[type="{elem_type}"]')

        # Add class if unique-looking (first class only)
        elem_class = element.get("class")
        if elem_class:
            if isinstance(elem_class, list) and len(elem_class) > 0:
                first_class = elem_class[0]
            else:
                first_class = str(elem_class).split()[0] if elem_class else None

            if first_class and not first_class.startswith(("js-", "ng-", "_")):
                selector_parts.append(f".{first_class}")

        # Add data-testid or data-id if available
        for attr in ["data-testid", "data-id", "data-cy"]:
            attr_val = element.get(attr)
            if attr_val and isinstance(attr_val, str):
                return f'{tag_name}[{attr}="{attr_val}"]'

        # For specific elements, add more context
        if tag_name == "input":
            placeholder = element.get("placeholder")
            if placeholder and isinstance(placeholder, str):
                # Use contains for placeholder (partial match)
                safe_placeholder = placeholder[:30].replace('"', '\\"')
                selector_parts.append(f'[placeholder*="{safe_placeholder}"]')

        if tag_name == "button" or tag_name == "a":
            # Try to use text content for buttons/links
            text = element.get_text(strip=True)[:20] if element.get_text(strip=True) else None
            if text:
                # Use :has-text or text content approach
                # For Playwright, we can use text selector
                return f'{tag_name}:has-text("{text}")'

        return "".join(selector_parts) if len(selector_parts) > 1 else None

    except Exception as e:
        print(f"[Selector] Error generating selector: {e}")
        return None


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
