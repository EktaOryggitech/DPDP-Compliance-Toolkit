"""
DPDP GUI Compliance Scanner - Privacy Notice Detector

Detects privacy notice compliance issues per DPDP Section 5.
"""
import re
from typing import List, Optional
from bs4 import BeautifulSoup

from app.detectors.base import BaseDetector
from app.models.finding import CheckType, Finding, FindingSeverity
from app.scanners.web.crawler import CrawledPage


class PrivacyNoticeDetector(BaseDetector):
    """
    Detector for DPDP Section 5 - Notice Requirements.

    Checks for:
    - Presence of privacy notice/policy
    - Required content in privacy notice
    - Readability and language accessibility
    - Prominent placement and accessibility
    """

    dpdp_section = "Section 5"
    description = "Detects privacy notice compliance issues"

    # Keywords indicating privacy notice pages
    PRIVACY_KEYWORDS = [
        "privacy policy", "privacy notice", "data protection",
        "गोपनीयता नीति", "गोपनीयता सूचना", "डेटा संरक्षण",
        "personal data", "personal information",
        "व्यक्तिगत डेटा", "व्यक्तिगत जानकारी",
    ]

    # Required elements in privacy notice (DPDP Section 5)
    REQUIRED_ELEMENTS = {
        "data_collected": [
            "personal data", "information we collect", "data we collect",
            "types of data", "categories of data",
            "एकत्रित डेटा", "हम एकत्र करते हैं",
        ],
        "purpose": [
            "purpose", "why we collect", "how we use", "use of data",
            "उद्देश्य", "हम क्यों एकत्र करते हैं", "उपयोग",
        ],
        "data_fiduciary": [
            "data fiduciary", "controller", "company", "organization",
            "who we are", "about us", "contact",
            "डेटा न्यासी", "कंपनी", "संगठन", "संपर्क",
        ],
        "rights": [
            "your rights", "data subject rights", "rights of the principal",
            "access", "correction", "erasure", "withdraw consent",
            "आपके अधिकार", "पहुंच", "सुधार", "विलोपन", "सहमति वापस",
        ],
        "grievance": [
            "grievance", "complaint", "contact us", "dpo", "data protection officer",
            "शिकायत", "संपर्क करें", "डेटा संरक्षण अधिकारी",
        ],
    }

    async def detect(self, page: CrawledPage) -> List[Finding]:
        """Detect privacy notice issues on the page."""
        findings = []

        # Check if this is a privacy-related page
        is_privacy_page = self._is_privacy_page(page)

        # Check for privacy notice link on non-privacy pages
        if not is_privacy_page:
            has_link = self._check_privacy_link(page)
            if not has_link:
                findings.append(Finding(
                    check_type=CheckType.PRIVACY_NOTICE_MISSING_LINK,
                    severity=FindingSeverity.HIGH,
                    title="Privacy notice link not found",
                    description="No link to privacy policy/notice found on this page. Users should be able to easily access privacy information.",
                    page_url=page.url,
                    dpdp_section=self.dpdp_section,
                    remediation="Add a prominent link to the privacy notice in the footer or navigation menu.",
                ))
        else:
            # Analyze privacy notice content
            content_findings = await self._analyze_privacy_content(page)
            findings.extend(content_findings)

        return findings

    def _is_privacy_page(self, page: CrawledPage) -> bool:
        """Check if this page is a privacy notice/policy page."""
        # Check URL
        url_lower = page.url.lower()
        if any(kw.replace(" ", "-") in url_lower or kw.replace(" ", "_") in url_lower
               for kw in ["privacy policy", "privacy-policy", "privacy_policy",
                          "privacy-notice", "data-protection"]):
            return True

        # Check title
        title_lower = page.title.lower() if page.title else ""
        if any(kw in title_lower for kw in self.PRIVACY_KEYWORDS):
            return True

        # Check page content heading
        soup = BeautifulSoup(page.html_content, "html.parser")
        h1_tags = soup.find_all("h1")
        for h1 in h1_tags:
            h1_text = h1.get_text().lower()
            if any(kw in h1_text for kw in self.PRIVACY_KEYWORDS):
                return True

        return False

    def _check_privacy_link(self, page: CrawledPage) -> bool:
        """Check if page has a link to privacy notice."""
        soup = BeautifulSoup(page.html_content, "html.parser")

        # Check all links
        for link in soup.find_all("a"):
            href = link.get("href", "").lower()
            text = link.get_text().lower()

            privacy_patterns = [
                "privacy", "data-protection", "data_protection",
                "गोपनीयता", "निजता",
            ]

            if any(p in href or p in text for p in privacy_patterns):
                return True

        return False

    async def _analyze_privacy_content(self, page: CrawledPage) -> List[Finding]:
        """Analyze privacy notice content for required elements."""
        findings = []
        soup = BeautifulSoup(page.html_content, "html.parser")
        text_content = soup.get_text().lower()

        # Check for each required element
        for element_name, keywords in self.REQUIRED_ELEMENTS.items():
            found = any(kw in text_content for kw in keywords)

            if not found:
                check_type_map = {
                    "data_collected": CheckType.PRIVACY_NOTICE_MISSING_DATA_TYPES,
                    "purpose": CheckType.PRIVACY_NOTICE_MISSING_PURPOSE,
                    "data_fiduciary": CheckType.PRIVACY_NOTICE_MISSING_FIDUCIARY,
                    "rights": CheckType.PRIVACY_NOTICE_MISSING_RIGHTS,
                    "grievance": CheckType.PRIVACY_NOTICE_MISSING_GRIEVANCE,
                }

                title_map = {
                    "data_collected": "Missing description of personal data collected",
                    "purpose": "Missing purpose of data collection",
                    "data_fiduciary": "Missing Data Fiduciary identification",
                    "rights": "Missing Data Principal rights information",
                    "grievance": "Missing grievance redressal mechanism",
                }

                findings.append(Finding(
                    check_type=check_type_map.get(element_name, CheckType.PRIVACY_NOTICE_INCOMPLETE),
                    severity=FindingSeverity.HIGH if element_name in ["data_collected", "purpose", "grievance"] else Severity.MEDIUM,
                    title=title_map.get(element_name, f"Missing {element_name}"),
                    description=f"Privacy notice does not contain required information about {element_name.replace('_', ' ')}. This is required under DPDP Section 5.",
                    page_url=page.url,
                    dpdp_section=self.dpdp_section,
                    remediation=f"Add clear information about {element_name.replace('_', ' ')} to the privacy notice.",
                ))

        # Check for language accessibility (Hindi)
        hindi_pattern = re.compile(r'[\u0900-\u097F]')
        has_hindi = bool(hindi_pattern.search(text_content))

        if not has_hindi:
            findings.append(Finding(
                check_type=CheckType.PRIVACY_NOTICE_LANGUAGE,
                severity=FindingSeverity.MEDIUM,
                title="Privacy notice not available in Hindi",
                description="Privacy notice appears to be only in English. DPDP recommends notices be in languages the user understands, including Hindi for Indian users.",
                page_url=page.url,
                dpdp_section=self.dpdp_section,
                remediation="Provide privacy notice in Hindi and other relevant Indian languages.",
            ))

        return findings
