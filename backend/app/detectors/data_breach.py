"""
DPDP GUI Compliance Scanner - Data Breach Notification Detector

Detects compliance issues related to data breach notification per DPDP requirements.
"""
import re
from typing import List
from bs4 import BeautifulSoup

from app.detectors.base import BaseDetector
from app.models.finding import CheckType, Finding, FindingSeverity
from app.scanners.web.crawler import CrawledPage


class DataBreachNotificationDetector(BaseDetector):
    """
    Detector for Data Breach Notification compliance.

    DPDP Requirements:
    - Data Fiduciary must notify the Data Protection Board of breaches
    - Affected Data Principals must be notified
    - Notification must be in prescribed manner and timeframe

    Checks for:
    - Breach notification policy
    - Contact information for breach reporting
    - Timeline commitments
    """

    dpdp_section = "Section 8(6)"
    description = "Detects data breach notification policy compliance"

    BREACH_NOTIFICATION_KEYWORDS = [
        # English
        "data breach", "security breach", "security incident",
        "breach notification", "notify you", "inform you of breach",
        "compromised", "unauthorized access", "data leak",
        "incident response", "breach disclosure",
        # Hindi
        "डेटा उल्लंघन", "सुरक्षा उल्लंघन", "सुरक्षा घटना",
        "उल्लंघन सूचना", "अनधिकृत पहुंच",
    ]

    NOTIFICATION_TIMELINE_PATTERNS = [
        r'(?:within|in)\s*(?:\d+|24|48|72)\s*hours?',
        r'(?:within|in)\s*(?:\d+|one|two|three|seven)\s*(?:days?|business days?)',
        r'(?:promptly|immediately|without delay)',
        r'as soon as (?:practicable|possible)',
    ]

    DPB_KEYWORDS = [
        "data protection board", "dpb", "regulatory authority",
        "data protection authority", "supervisory authority",
        "डेटा संरक्षण बोर्ड",
    ]

    async def detect(self, page: CrawledPage) -> List[Finding]:
        """Detect data breach notification policy issues."""
        findings = []

        soup = BeautifulSoup(page.html_content, "html.parser")
        text_content = soup.get_text().lower()

        # Only check privacy-related pages
        if not self._is_privacy_page(page.url, text_content):
            return findings

        # Check for breach notification policy
        has_breach_policy = any(
            keyword in text_content for keyword in self.BREACH_NOTIFICATION_KEYWORDS
        )

        if not has_breach_policy:
            findings.append(Finding(
                check_type=CheckType.BREACH_NOTIFICATION_MISSING,
                severity=FindingSeverity.HIGH,
                title="No data breach notification policy found",
                description="Privacy policy does not describe the data breach notification process. DPDP requires notifying affected users and the Data Protection Board in case of a breach.",
                page_url=page.url,
                dpdp_section=self.dpdp_section,
                remediation="Add a data breach notification section describing how and when users will be notified of any security incidents affecting their data.",
            ))
        else:
            # Check for notification timeline
            has_timeline = any(
                re.search(pattern, text_content, re.IGNORECASE)
                for pattern in self.NOTIFICATION_TIMELINE_PATTERNS
            )

            if not has_timeline:
                findings.append(Finding(
                    check_type=CheckType.BREACH_NOTIFICATION_NO_TIMELINE,
                    severity=FindingSeverity.MEDIUM,
                    title="Breach notification timeline not specified",
                    description="Breach notification policy exists but doesn't specify a notification timeline.",
                    page_url=page.url,
                    dpdp_section=self.dpdp_section,
                    remediation="Specify the timeframe within which users will be notified of a data breach (e.g., within 72 hours of becoming aware).",
                ))

            # Check for DPB notification mention
            has_dpb_mention = any(
                keyword in text_content for keyword in self.DPB_KEYWORDS
            )

            if not has_dpb_mention:
                findings.append(Finding(
                    check_type=CheckType.BREACH_NOTIFICATION_NO_DPB,
                    severity=FindingSeverity.MEDIUM,
                    title="No mention of Data Protection Board notification",
                    description="Breach policy doesn't mention notification to the Data Protection Board. DPDP requires notifying the DPB of breaches.",
                    page_url=page.url,
                    dpdp_section=self.dpdp_section,
                    remediation="Add information about notification to the Data Protection Board of India in case of a data breach.",
                ))

        return findings

    def _is_privacy_page(self, url: str, text_content: str) -> bool:
        """Check if this is a privacy-related page."""
        url_lower = url.lower()

        if any(p in url_lower for p in ["privacy", "policy", "security", "terms"]):
            return True

        return "privacy" in text_content[:1000] or "data protection" in text_content[:1000]


class SignificantDataFiduciaryDetector(BaseDetector):
    """
    Detector for Significant Data Fiduciary obligations.

    DPDP designates certain entities as "Significant Data Fiduciaries"
    with additional obligations including:
    - Appointing a Data Protection Officer (DPO)
    - Independent data auditor
    - Data Protection Impact Assessment (DPIA)
    """

    dpdp_section = "Section 10"
    description = "Detects Significant Data Fiduciary compliance"

    DPO_KEYWORDS = [
        "data protection officer", "dpo", "privacy officer",
        "chief privacy officer", "cpo",
        "डेटा संरक्षण अधिकारी",
    ]

    AUDIT_KEYWORDS = [
        "data audit", "privacy audit", "independent audit",
        "external audit", "third-party audit", "compliance audit",
        "डेटा ऑडिट", "गोपनीयता ऑडिट",
    ]

    DPIA_KEYWORDS = [
        "data protection impact assessment", "dpia",
        "privacy impact assessment", "pia", "risk assessment",
        "डेटा संरक्षण प्रभाव मूल्यांकन",
    ]

    async def detect(self, page: CrawledPage) -> List[Finding]:
        """Detect Significant Data Fiduciary compliance issues."""
        findings = []

        soup = BeautifulSoup(page.html_content, "html.parser")
        text_content = soup.get_text().lower()

        # Only check privacy-related pages
        if not self._is_privacy_page(page.url, text_content):
            return findings

        # Check indicators that this might be a Significant Data Fiduciary
        sdf_indicators = [
            "significant data fiduciary", "large scale processing",
            "million users", "crore users", "national security",
            "government", "public authority",
        ]

        is_likely_sdf = any(indicator in text_content for indicator in sdf_indicators)

        # Only flag if there are SDF indicators but missing compliance elements
        if is_likely_sdf:
            # Check for DPO
            has_dpo = any(keyword in text_content for keyword in self.DPO_KEYWORDS)

            if not has_dpo:
                findings.append(Finding(
                    check_type=CheckType.SDF_DPO_MISSING,
                    severity=FindingSeverity.HIGH,
                    title="No Data Protection Officer mentioned",
                    description="Entity appears to be a Significant Data Fiduciary but no DPO is mentioned. DPDP Section 10 requires SDFs to appoint a DPO.",
                    page_url=page.url,
                    dpdp_section=self.dpdp_section,
                    remediation="Appoint a Data Protection Officer and publish their contact details.",
                ))

            # Check for audit mention
            has_audit = any(keyword in text_content for keyword in self.AUDIT_KEYWORDS)

            if not has_audit:
                findings.append(Finding(
                    check_type=CheckType.SDF_AUDIT_MISSING,
                    severity=FindingSeverity.MEDIUM,
                    title="No data audit information found",
                    description="Significant Data Fiduciary should conduct periodic data audits. No audit information found.",
                    page_url=page.url,
                    dpdp_section=self.dpdp_section,
                    remediation="Conduct and document periodic data protection audits by an independent auditor.",
                ))

        return findings

    def _is_privacy_page(self, url: str, text_content: str) -> bool:
        """Check if this is a privacy-related page."""
        url_lower = url.lower()

        if any(p in url_lower for p in ["privacy", "policy", "about", "compliance"]):
            return True

        return "privacy" in text_content[:1000]
