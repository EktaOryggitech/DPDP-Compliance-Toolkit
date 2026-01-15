"""
DPDP GUI Compliance Scanner - Children's Data Detector

Detects compliance issues related to children's personal data per DPDP Section 9.
"""
import re
from typing import List, Dict, Any
from bs4 import BeautifulSoup

from app.detectors.base import BaseDetector
from app.models.finding import CheckType, Finding, FindingSeverity
from app.scanners.web.crawler import CrawledPage


class ChildrenDataDetector(BaseDetector):
    """
    Detector for DPDP Section 9 - Processing of Children's Data.

    DPDP Section 9 Requirements:
    - Verifiable consent from parent/guardian before processing children's data
    - No tracking, behavioral monitoring, or targeted advertising for children
    - Age verification mechanisms
    - Special protections for children under 18

    Checks for:
    - Age verification/gate presence
    - Parental consent mechanisms
    - Prohibition of behavioral tracking for children
    - Children-targeted content without proper safeguards
    """

    dpdp_section = "Section 9"
    description = "Detects children's data protection compliance issues"

    # Indicators that site may collect children's data
    CHILDREN_CONTENT_INDICATORS = [
        # English
        "kids", "children", "child", "minor", "teen", "teenager",
        "school", "student", "education", "learning", "games for kids",
        "parental", "family", "young", "youth", "junior",
        "cartoon", "animation", "toys", "playground",
        # Hindi
        "बच्चे", "बच्चों", "बाल", "किशोर", "छात्र", "शिक्षा",
        "स्कूल", "विद्यालय", "खेल", "कार्टून", "माता-पिता",
    ]

    # Age verification patterns
    AGE_VERIFICATION_PATTERNS = [
        r"(?:enter|confirm|verify).*(?:age|birth|dob|date of birth)",
        r"(?:age|birth).*(?:verification|gate|check)",
        r"(?:i am|i'm).*(?:18|thirteen|18\+|adult)",
        r"(?:born|birthday).*(?:before|after|year)",
        r"(?:are you|confirm).*(?:18|adult|years old)",
        r"(?:under|over).*(?:18|13|age)",
        r"आयु.*(?:सत्यापन|जांच)",
        r"(?:18|१८).*(?:वर्ष|साल)",
    ]

    # Parental consent patterns
    PARENTAL_CONSENT_PATTERNS = [
        r"parent(?:al)?.*consent",
        r"guardian.*(?:consent|permission|approval)",
        r"(?:parent|guardian).*(?:email|contact|verify)",
        r"(?:consent|permission).*(?:parent|guardian)",
        r"माता-पिता.*सहमति",
        r"अभिभावक.*अनुमति",
    ]

    # Tracking/behavioral advertising indicators
    TRACKING_INDICATORS = [
        "behavioral advertising", "targeted ads", "personalized advertising",
        "interest-based", "tracking cookies", "analytics cookies",
        "retargeting", "remarketing", "profiling",
        "व्यवहार विज्ञापन", "लक्षित विज्ञापन",
    ]

    async def detect(self, page: CrawledPage) -> List[Finding]:
        """Detect children's data protection issues on the page."""
        findings = []

        soup = BeautifulSoup(page.html_content, "html.parser")
        text_content = soup.get_text().lower()

        # Check if this appears to be children-targeted content
        is_children_site = self._is_children_targeted(text_content, page.url)

        if is_children_site:
            # Check for age verification
            age_findings = self._check_age_verification(soup, text_content, page)
            findings.extend(age_findings)

            # Check for parental consent mechanism
            consent_findings = self._check_parental_consent(soup, text_content, page)
            findings.extend(consent_findings)

            # Check for prohibited tracking
            tracking_findings = self._check_tracking_prohibition(soup, text_content, page)
            findings.extend(tracking_findings)

        # Check forms that collect age/DOB
        form_findings = self._check_age_collection_forms(soup, page)
        findings.extend(form_findings)

        return findings

    def _is_children_targeted(self, text_content: str, url: str) -> bool:
        """Determine if the site/page is targeted at children."""
        url_lower = url.lower()

        # Check URL patterns
        children_url_patterns = ["kids", "children", "junior", "teen", "youth", "school"]
        if any(pattern in url_lower for pattern in children_url_patterns):
            return True

        # Check content for children indicators
        indicator_count = sum(
            1 for indicator in self.CHILDREN_CONTENT_INDICATORS
            if indicator in text_content
        )

        # If multiple indicators found, likely children-targeted
        return indicator_count >= 3

    def _check_age_verification(
        self,
        soup: BeautifulSoup,
        text_content: str,
        page: CrawledPage,
    ) -> List[Finding]:
        """Check for proper age verification mechanisms."""
        findings = []

        # Look for age verification patterns
        has_age_verification = any(
            re.search(pattern, text_content, re.IGNORECASE)
            for pattern in self.AGE_VERIFICATION_PATTERNS
        )

        # Look for age input fields
        age_inputs = soup.find_all("input", attrs={
            "type": lambda x: x in ["date", "number", "text"],
            "name": lambda x: x and any(
                term in x.lower() for term in ["age", "dob", "birth", "year"]
            ) if x else False,
        })

        # Check for age dropdown/select
        age_selects = soup.find_all("select", attrs={
            "name": lambda x: x and any(
                term in x.lower() for term in ["age", "year", "month", "day", "birth"]
            ) if x else False,
        })

        has_age_inputs = len(age_inputs) > 0 or len(age_selects) > 0

        if not has_age_verification and not has_age_inputs:
            findings.append(Finding(
                check_type=CheckType.CHILDREN_AGE_VERIFICATION_MISSING,
                severity=FindingSeverity.CRITICAL,
                title="No age verification mechanism found",
                description="This appears to be a children-targeted site but lacks age verification. DPDP Section 9 requires verification before processing children's data.",
                page_url=page.url,
                dpdp_section=self.dpdp_section,
                remediation="Implement a robust age verification mechanism (age gate, date of birth input) before collecting any personal data.",
            ))

        return findings

    def _check_parental_consent(
        self,
        soup: BeautifulSoup,
        text_content: str,
        page: CrawledPage,
    ) -> List[Finding]:
        """Check for parental consent mechanisms."""
        findings = []

        # Look for parental consent patterns
        has_parental_consent = any(
            re.search(pattern, text_content, re.IGNORECASE)
            for pattern in self.PARENTAL_CONSENT_PATTERNS
        )

        # Look for parent email/contact fields
        parent_fields = soup.find_all("input", attrs={
            "name": lambda x: x and any(
                term in x.lower() for term in ["parent", "guardian", "father", "mother"]
            ) if x else False,
        })

        if not has_parental_consent and len(parent_fields) == 0:
            # Check if there's data collection happening
            has_forms = len(soup.find_all("form")) > 0

            if has_forms:
                findings.append(Finding(
                    check_type=CheckType.CHILDREN_PARENTAL_CONSENT_MISSING,
                    severity=FindingSeverity.CRITICAL,
                    title="No parental consent mechanism found",
                    description="Children-targeted site collects data but lacks verifiable parental consent mechanism. DPDP Section 9 requires parental/guardian consent for processing children's data.",
                    page_url=page.url,
                    dpdp_section=self.dpdp_section,
                    remediation="Implement verifiable parental consent: parent email verification, signed consent form, or other approved methods.",
                ))

        return findings

    def _check_tracking_prohibition(
        self,
        soup: BeautifulSoup,
        text_content: str,
        page: CrawledPage,
    ) -> List[Finding]:
        """Check for prohibited tracking/behavioral advertising."""
        findings = []

        # Check for tracking indicators
        tracking_found = []
        for indicator in self.TRACKING_INDICATORS:
            if indicator in text_content:
                tracking_found.append(indicator)

        # Check for tracking scripts
        scripts = soup.find_all("script", src=True)
        tracking_scripts = []

        tracking_domains = [
            "google-analytics", "googletagmanager", "facebook",
            "doubleclick", "adsense", "adroll", "criteo",
            "taboola", "outbrain", "hotjar", "mixpanel",
        ]

        for script in scripts:
            src = script.get("src", "").lower()
            for domain in tracking_domains:
                if domain in src:
                    tracking_scripts.append(domain)

        if tracking_found or tracking_scripts:
            findings.append(Finding(
                check_type=CheckType.CHILDREN_TRACKING_DETECTED,
                severity=FindingSeverity.CRITICAL,
                title="Tracking/behavioral advertising detected on children's site",
                description=f"DPDP Section 9 prohibits tracking, behavioral monitoring, and targeted advertising for children. Found: {', '.join(tracking_found + tracking_scripts)[:200]}",
                page_url=page.url,
                dpdp_section=self.dpdp_section,
                remediation="Remove all tracking, analytics, and behavioral advertising from children-targeted sections. Only essential cookies should be used.",
            ))

        # Check for third-party cookies mention without exception for children
        cookie_text = text_content
        if "third party" in cookie_text and "cookie" in cookie_text:
            if not any(term in cookie_text for term in ["except children", "not for children", "disable for minors"]):
                findings.append(Finding(
                    check_type=CheckType.CHILDREN_THIRD_PARTY_SHARING,
                    severity=FindingSeverity.HIGH,
                    title="Third-party data sharing on children's site",
                    description="Third-party cookies/data sharing detected without explicit exemption for children's data.",
                    page_url=page.url,
                    dpdp_section=self.dpdp_section,
                    remediation="Disable third-party data sharing for users identified as children. Implement age-gated cookie consent.",
                ))

        return findings

    def _check_age_collection_forms(
        self,
        soup: BeautifulSoup,
        page: CrawledPage,
    ) -> List[Finding]:
        """Check forms that collect age/DOB for proper handling."""
        findings = []

        forms = soup.find_all("form")

        for form in forms:
            # Find age/DOB fields
            age_fields = form.find_all(["input", "select"], attrs={
                "name": lambda x: x and any(
                    term in x.lower() for term in ["age", "dob", "birth", "year"]
                ) if x else False,
            })

            if age_fields:
                # Check if there's accompanying text about children's data
                form_text = form.get_text().lower()

                has_children_notice = any(
                    term in form_text for term in [
                        "under 18", "minor", "children", "parental consent",
                        "guardian", "18 years",
                        "18 वर्ष", "नाबालिग", "अभिभावक",
                    ]
                )

                if not has_children_notice:
                    findings.append(Finding(
                        check_type=CheckType.CHILDREN_DATA_COLLECTION_NO_NOTICE,
                        severity=FindingSeverity.MEDIUM,
                        title="Age collection without children's data handling notice",
                        description="Form collects age/date of birth but doesn't explain how children's data will be handled differently.",
                        page_url=page.url,
                        element_html=str(form)[:500],
                        dpdp_section=self.dpdp_section,
                        remediation="Add clear notice about how data will be handled if user is under 18, including parental consent requirements.",
                    ))

        return findings
