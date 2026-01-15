"""
DPDP GUI Compliance Scanner - Data Principal Rights Detector

Detects compliance issues related to Data Principal rights per DPDP Section 11-14.
"""
import re
from typing import List, Dict, Any
from bs4 import BeautifulSoup

from app.detectors.base import BaseDetector
from app.models.finding import CheckType, Finding, FindingSeverity
from app.scanners.web.crawler import CrawledPage


class DataPrincipalRightsDetector(BaseDetector):
    """
    Detector for DPDP Sections 11-14 - Data Principal Rights and Obligations.

    Section 11: Right to access information about personal data
    Section 12: Right to correction and erasure
    Section 13: Grievance redressal
    Section 14: Nomination by Data Principal

    Checks for:
    - Access request mechanism
    - Correction/update mechanism
    - Deletion/erasure mechanism
    - Grievance officer details
    - Nomination provisions
    """

    dpdp_section = "Section 11-14"
    description = "Detects Data Principal rights compliance issues"

    # Access rights keywords
    ACCESS_RIGHTS_KEYWORDS = [
        # English
        "access your data", "access my data", "view your data", "view my data",
        "download your data", "download my data", "data portability",
        "request your data", "obtain a copy", "right to access",
        "data access request", "subject access request", "sar",
        # Hindi
        "अपना डेटा देखें", "डेटा एक्सेस", "डेटा प्राप्त करें",
    ]

    # Correction rights keywords
    CORRECTION_KEYWORDS = [
        # English
        "correct your data", "update your data", "rectify", "rectification",
        "edit your information", "modify your data", "amend",
        "right to correction", "update profile", "edit profile",
        # Hindi
        "डेटा सुधारें", "जानकारी अपडेट", "संशोधन",
    ]

    # Erasure/deletion keywords
    ERASURE_KEYWORDS = [
        # English
        "delete your data", "erase your data", "right to erasure",
        "right to be forgotten", "delete my account", "remove my data",
        "data deletion", "account deletion", "close account",
        "permanently delete", "request deletion",
        # Hindi
        "डेटा हटाएं", "खाता हटाएं", "डेटा मिटाएं", "विलोपन",
    ]

    # Grievance mechanism keywords
    GRIEVANCE_KEYWORDS = [
        # English
        "grievance", "grievance officer", "data protection officer", "dpo",
        "complaint", "raise a concern", "file a complaint",
        "grievance redressal", "nodal officer", "privacy officer",
        # Hindi
        "शिकायत", "शिकायत अधिकारी", "डेटा संरक्षण अधिकारी",
        "शिकायत निवारण",
    ]

    # Nomination keywords
    NOMINATION_KEYWORDS = [
        # English
        "nominate", "nomination", "nominee", "authorized person",
        "in case of death", "incapacity", "legal heir",
        # Hindi
        "नामांकन", "नामांकित व्यक्ति", "उत्तराधिकारी",
    ]

    async def detect(self, page: CrawledPage) -> List[Finding]:
        """Detect Data Principal rights issues on the page."""
        findings = []

        soup = BeautifulSoup(page.html_content, "html.parser")
        text_content = soup.get_text().lower()

        # Check if this is a privacy-related page
        is_privacy_page = self._is_rights_related_page(page.url, text_content)

        if is_privacy_page:
            # Check for Section 11 - Access rights
            access_findings = self._check_access_rights(text_content, page)
            findings.extend(access_findings)

            # Check for Section 12 - Correction and erasure rights
            correction_findings = self._check_correction_rights(text_content, page)
            findings.extend(correction_findings)

            erasure_findings = self._check_erasure_rights(text_content, page)
            findings.extend(erasure_findings)

            # Check for Section 13 - Grievance mechanism
            grievance_findings = self._check_grievance_mechanism(soup, text_content, page)
            findings.extend(grievance_findings)

            # Check for Section 14 - Nomination
            nomination_findings = self._check_nomination_provision(text_content, page)
            findings.extend(nomination_findings)

        return findings

    def _is_rights_related_page(self, url: str, text_content: str) -> bool:
        """Check if this page should contain rights information."""
        url_lower = url.lower()

        rights_url_patterns = [
            "privacy", "policy", "terms", "rights", "data-subject",
            "your-data", "account", "settings", "profile",
        ]

        if any(pattern in url_lower for pattern in rights_url_patterns):
            return True

        # Check content
        rights_indicators = [
            "privacy policy", "your rights", "data protection",
            "personal data", "your information",
        ]

        return any(indicator in text_content for indicator in rights_indicators)

    def _check_access_rights(self, text_content: str, page: CrawledPage) -> List[Finding]:
        """Check for Section 11 - Right to access personal data."""
        findings = []

        has_access_info = any(
            keyword in text_content for keyword in self.ACCESS_RIGHTS_KEYWORDS
        )

        if not has_access_info:
            findings.append(Finding(
                check_type=CheckType.RIGHTS_ACCESS_MISSING,
                severity=FindingSeverity.HIGH,
                title="No data access mechanism described",
                description="Privacy policy does not describe how users can access their personal data. DPDP Section 11 requires providing access to personal data upon request.",
                page_url=page.url,
                dpdp_section="Section 11",
                remediation="Add clear information about how users can request and obtain a copy of their personal data, including the process and timeline.",
            ))

        return findings

    def _check_correction_rights(self, text_content: str, page: CrawledPage) -> List[Finding]:
        """Check for Section 12 - Right to correction."""
        findings = []

        has_correction_info = any(
            keyword in text_content for keyword in self.CORRECTION_KEYWORDS
        )

        if not has_correction_info:
            findings.append(Finding(
                check_type=CheckType.RIGHTS_CORRECTION_MISSING,
                severity=FindingSeverity.HIGH,
                title="No data correction mechanism described",
                description="Privacy policy does not describe how users can correct/update their personal data. DPDP Section 12 requires allowing correction of inaccurate data.",
                page_url=page.url,
                dpdp_section="Section 12",
                remediation="Add information about how users can request correction of inaccurate or incomplete personal data.",
            ))

        return findings

    def _check_erasure_rights(self, text_content: str, page: CrawledPage) -> List[Finding]:
        """Check for Section 12 - Right to erasure."""
        findings = []

        has_erasure_info = any(
            keyword in text_content for keyword in self.ERASURE_KEYWORDS
        )

        if not has_erasure_info:
            findings.append(Finding(
                check_type=CheckType.RIGHTS_ERASURE_MISSING,
                severity=FindingSeverity.HIGH,
                title="No data deletion mechanism described",
                description="Privacy policy does not describe how users can delete their personal data. DPDP Section 12 requires allowing erasure when data is no longer needed.",
                page_url=page.url,
                dpdp_section="Section 12",
                remediation="Add clear information about how users can request deletion of their personal data and account.",
            ))

        return findings

    def _check_grievance_mechanism(
        self,
        soup: BeautifulSoup,
        text_content: str,
        page: CrawledPage,
    ) -> List[Finding]:
        """Check for Section 13 - Grievance redressal mechanism."""
        findings = []

        has_grievance_info = any(
            keyword in text_content for keyword in self.GRIEVANCE_KEYWORDS
        )

        if not has_grievance_info:
            findings.append(Finding(
                check_type=CheckType.GRIEVANCE_MECHANISM_MISSING,
                severity=FindingSeverity.CRITICAL,
                title="No grievance redressal mechanism found",
                description="No grievance officer or complaint mechanism described. DPDP Section 13 mandates a grievance redressal mechanism.",
                page_url=page.url,
                dpdp_section="Section 13",
                remediation="Appoint a Grievance Officer and publish their name, contact details, and the grievance submission process.",
            ))
        else:
            # Check for grievance officer contact details
            contact_findings = self._check_grievance_contact_details(soup, text_content, page)
            findings.extend(contact_findings)

        return findings

    def _check_grievance_contact_details(
        self,
        soup: BeautifulSoup,
        text_content: str,
        page: CrawledPage,
    ) -> List[Finding]:
        """Check if grievance officer contact details are complete."""
        findings = []

        # Look for email pattern
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        has_email = bool(re.search(email_pattern, text_content))

        # Look for phone pattern (Indian format)
        phone_pattern = r'(?:\+91|0)?[6-9]\d{9}'
        has_phone = bool(re.search(phone_pattern, text_content))

        # Look for name/designation
        name_patterns = [
            r'grievance officer\s*:\s*[\w\s]+',
            r'dpo\s*:\s*[\w\s]+',
            r'data protection officer\s*:\s*[\w\s]+',
            r'nodal officer\s*:\s*[\w\s]+',
        ]
        has_name = any(re.search(p, text_content, re.IGNORECASE) for p in name_patterns)

        # Check for response timeline
        timeline_patterns = [
            r'\d+\s*(?:days?|hours?|business days?)',
            r'within\s+\d+',
            r'response time',
        ]
        has_timeline = any(re.search(p, text_content, re.IGNORECASE) for p in timeline_patterns)

        missing = []
        if not has_email:
            missing.append("email address")
        if not has_name:
            missing.append("officer name/designation")
        if not has_timeline:
            missing.append("response timeline")

        if missing:
            findings.append(Finding(
                check_type=CheckType.GRIEVANCE_DETAILS_INCOMPLETE,
                severity=FindingSeverity.MEDIUM,
                title="Incomplete grievance officer details",
                description=f"Grievance mechanism mentioned but missing: {', '.join(missing)}. Complete contact details are required.",
                page_url=page.url,
                dpdp_section="Section 13",
                remediation=f"Add the following to grievance section: {', '.join(missing)}. Response should be within 7 days as per DPDP.",
            ))

        return findings

    def _check_nomination_provision(self, text_content: str, page: CrawledPage) -> List[Finding]:
        """Check for Section 14 - Nomination provisions."""
        findings = []

        has_nomination_info = any(
            keyword in text_content for keyword in self.NOMINATION_KEYWORDS
        )

        # This is a lower priority check as not all services need nomination
        # Only flag if other rights are mentioned but nomination is missing
        has_other_rights = any(
            keyword in text_content
            for keyword in self.ACCESS_RIGHTS_KEYWORDS + self.ERASURE_KEYWORDS
        )

        if has_other_rights and not has_nomination_info:
            findings.append(Finding(
                check_type=CheckType.NOMINATION_PROVISION_MISSING,
                severity=FindingSeverity.LOW,
                title="No nomination provision described",
                description="Privacy policy describes data rights but doesn't mention nomination of another person to exercise rights (in case of death/incapacity). DPDP Section 14 allows for nomination.",
                page_url=page.url,
                dpdp_section="Section 14",
                remediation="Add information about how users can nominate someone to exercise their data rights in case of death or incapacity.",
            ))

        return findings


class DataRetentionDetector(BaseDetector):
    """
    Detector for data retention policy compliance.

    Checks for:
    - Clear retention periods
    - Retention justification
    - Deletion after purpose fulfilled
    """

    dpdp_section = "Section 8"
    description = "Detects data retention policy compliance issues"

    RETENTION_KEYWORDS = [
        # English
        "retention", "retain", "keep your data", "store your data",
        "how long", "data storage period", "delete after",
        "retention period", "data lifecycle",
        # Hindi
        "डेटा संग्रहण", "कितने समय तक", "डेटा रखना",
    ]

    async def detect(self, page: CrawledPage) -> List[Finding]:
        """Detect data retention policy issues."""
        findings = []

        soup = BeautifulSoup(page.html_content, "html.parser")
        text_content = soup.get_text().lower()

        # Only check privacy-related pages
        if not self._is_privacy_page(page.url, text_content):
            return findings

        has_retention_info = any(
            keyword in text_content for keyword in self.RETENTION_KEYWORDS
        )

        if not has_retention_info:
            findings.append(Finding(
                check_type=CheckType.DATA_RETENTION_MISSING,
                severity=FindingSeverity.MEDIUM,
                title="No data retention policy found",
                description="Privacy policy does not describe how long personal data is retained. DPDP requires data to be deleted when no longer needed for the stated purpose.",
                page_url=page.url,
                dpdp_section=self.dpdp_section,
                remediation="Add clear information about data retention periods for each type of data collected and the criteria for determining retention.",
            ))
        else:
            # Check for specific retention periods
            period_patterns = [
                r'\d+\s*(?:days?|months?|years?)',
                r'(?:one|two|three|five|seven|ten)\s*(?:days?|months?|years?)',
            ]

            has_specific_period = any(
                re.search(p, text_content, re.IGNORECASE) for p in period_patterns
            )

            if not has_specific_period:
                findings.append(Finding(
                    check_type=CheckType.DATA_RETENTION_VAGUE,
                    severity=FindingSeverity.LOW,
                    title="Data retention period not specific",
                    description="Retention policy mentioned but no specific time periods given. Vague language like 'as long as necessary' is insufficient.",
                    page_url=page.url,
                    dpdp_section=self.dpdp_section,
                    remediation="Specify exact retention periods (e.g., '2 years from last activity') rather than vague statements.",
                ))

        return findings

    def _is_privacy_page(self, url: str, text_content: str) -> bool:
        """Check if this is a privacy-related page."""
        url_lower = url.lower()

        if any(p in url_lower for p in ["privacy", "policy", "terms", "data"]):
            return True

        return "privacy" in text_content[:1000] or "personal data" in text_content[:1000]
