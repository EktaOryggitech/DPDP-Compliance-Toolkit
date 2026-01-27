"""
DPDP GUI Compliance Scanner - Data Breach Notification Detector

Detects compliance issues related to data breach notification per DPDP requirements.
"""
import re
from typing import List
from bs4 import BeautifulSoup

from app.detectors.base import BaseDetector
from app.models.finding import CheckType, Finding, FindingSeverity, FindingStatus
from app.scanners.web.crawler import CrawledPage


def generate_visual_box(title: str, content_lines: List[str], width: int = 60) -> str:
    """Generate ASCII box diagram for visual representation."""
    lines = []
    border = "─" * (width - 2)
    lines.append(f"┌{border}┐")
    lines.append(f"│  {title:<{width-6}}  │")
    lines.append(f"├{border}┤")
    for line in content_lines:
        display_line = line[:width-6] if len(line) > width-6 else line
        lines.append(f"│  {display_line:<{width-6}}  │")
    lines.append(f"└{border}┘")
    return "\n".join(lines)


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
            visual_content = [
                "VIOLATION: No Data Breach Policy",
                "",
                "DPDP Section 8(6) - Mandatory Requirement",
                "",
                "Required Elements (NOT FOUND):",
                "  ✗ Breach notification commitment",
                "  ✗ Notification timeline",
                "  ✗ DPB notification process",
                "  ✗ User notification process",
                "",
                "Penalty: Up to ₹250 crore",
            ]
            visual_box = generate_visual_box("DATA BREACH POLICY MISSING", visual_content)

            findings.append(Finding(
                check_type=CheckType.OTHER,
                severity=FindingSeverity.HIGH,
                status=FindingStatus.FAIL,
                title="No data breach notification policy found",
                description="Privacy policy does not describe the data breach notification process. DPDP requires notifying affected users and the Data Protection Board in case of a breach.",
                location=page.url,
                dpdp_section=self.dpdp_section,
                remediation="Add a data breach notification section describing how and when users will be notified of any security incidents affecting their data.",
                extra_data={
                    "violation_type": "missing_breach_policy",
                    "keywords_searched": self.BREACH_NOTIFICATION_KEYWORDS[:5],
                    "code_fix_example": '''
<section id="data-breach">
  <h2>Data Breach Notification Policy</h2>

  <h3>Our Commitment</h3>
  <p>In the event of a data breach affecting your personal data,
  we will notify you promptly.</p>

  <h3>Notification Process</h3>
  <ol>
    <li>We will notify the Data Protection Board within 72 hours</li>
    <li>Affected users will be notified via email within 72 hours</li>
    <li>We will provide details of:
      <ul>
        <li>Nature of the breach</li>
        <li>Data categories affected</li>
        <li>Measures taken</li>
        <li>Steps you can take</li>
      </ul>
    </li>
  </ol>

  <h3>Report a Security Concern</h3>
  <p>Email: security@company.com</p>
</section>''',
                    "penalty_risk": "₹250 crore - DPDP Section 8(6) violation",
                    "visual_representation": visual_box,
                    "dpdp_reference": {
                        "section": "Section 8(6)",
                        "requirement": "Data Fiduciary must inform Data Protection Board and affected Data Principals of personal data breach",
                        "penalty": "Up to ₹250 crore"
                    },
                    "fix_steps": [
                        "Add 'Data Breach Notification' section in privacy policy",
                        "Commit to 72-hour notification timeline",
                        "Mention notification to Data Protection Board",
                        "Describe what information will be shared",
                        "Include security contact email",
                        "Include Hindi: डेटा उल्लंघन सूचना नीति"
                    ]
                }
            ))
        else:
            # Check for notification timeline
            has_timeline = any(
                re.search(pattern, text_content, re.IGNORECASE)
                for pattern in self.NOTIFICATION_TIMELINE_PATTERNS
            )

            if not has_timeline:
                visual_content = [
                    "ISSUE: No Notification Timeline",
                    "",
                    "Found: Breach policy exists",
                    "Missing: Specific notification timeline",
                    "",
                    "Required:",
                    "  ✗ '72 hours' or similar commitment",
                    "  ✗ 'within X days' specification",
                    "",
                    "Best Practice: 72 hours (GDPR standard)",
                ]
                visual_box = generate_visual_box("BREACH TIMELINE MISSING", visual_content)

                findings.append(Finding(
                    check_type=CheckType.OTHER,
                    severity=FindingSeverity.MEDIUM,
                    status=FindingStatus.FAIL,
                    title="Breach notification timeline not specified",
                    description="Breach notification policy exists but doesn't specify a notification timeline.",
                    location=page.url,
                    dpdp_section=self.dpdp_section,
                    remediation="Specify the timeframe within which users will be notified of a data breach (e.g., within 72 hours of becoming aware).",
                    extra_data={
                        "violation_type": "missing_breach_timeline",
                        "code_before": '''
<!-- Vague timeline (BAD) -->
<p>We will notify you promptly in case of a breach.</p>''',
                        "code_after": '''
<!-- Specific timeline (GOOD) -->
<p>In case of a data breach:</p>
<ul>
  <li>Data Protection Board: Notified within 72 hours</li>
  <li>Affected users: Notified within 72 hours via email</li>
  <li>Public disclosure: If required, within 7 days</li>
</ul>''',
                        "penalty_risk": "₹50 crore - Incomplete breach policy",
                        "visual_representation": visual_box,
                        "dpdp_reference": {
                            "section": "Section 8(6)",
                            "requirement": "Timely notification of data breach",
                            "penalty": "Up to ₹250 crore"
                        },
                        "fix_steps": [
                            "Add specific timeline (recommended: 72 hours)",
                            "Specify separate timelines for DPB and users",
                            "Use phrases like 'within 72 hours of discovery'"
                        ]
                    }
                ))

            # Check for DPB notification mention
            has_dpb_mention = any(
                keyword in text_content for keyword in self.DPB_KEYWORDS
            )

            if not has_dpb_mention:
                visual_content = [
                    "ISSUE: No DPB Notification Mentioned",
                    "",
                    "DPDP Requirement:",
                    "  Data Protection Board must be notified",
                    "  of all personal data breaches",
                    "",
                    "Missing Reference to:",
                    "  ✗ Data Protection Board (DPB)",
                    "  ✗ Regulatory notification",
                    "",
                    "This is a mandatory requirement",
                ]
                visual_box = generate_visual_box("DPB NOTIFICATION MISSING", visual_content)

                findings.append(Finding(
                    check_type=CheckType.OTHER,
                    severity=FindingSeverity.MEDIUM,
                    status=FindingStatus.FAIL,
                    title="No mention of Data Protection Board notification",
                    description="Breach policy doesn't mention notification to the Data Protection Board. DPDP requires notifying the DPB of breaches.",
                    location=page.url,
                    dpdp_section=self.dpdp_section,
                    remediation="Add information about notification to the Data Protection Board of India in case of a data breach.",
                    extra_data={
                        "violation_type": "missing_dpb_notification",
                        "code_fix_example": '''
<section id="regulatory-notification">
  <h3>Regulatory Notification</h3>
  <p>In compliance with DPDP Act, we will notify the
  <strong>Data Protection Board of India</strong> within 72 hours
  of becoming aware of any personal data breach.</p>

  <p>The notification will include:</p>
  <ul>
    <li>Nature and scope of breach</li>
    <li>Categories and approximate number of affected users</li>
    <li>Likely consequences of the breach</li>
    <li>Measures taken or proposed to address the breach</li>
  </ul>
</section>''',
                        "penalty_risk": "₹100 crore - Failure to notify regulatory authority",
                        "visual_representation": visual_box,
                        "dpdp_reference": {
                            "section": "Section 8(6)",
                            "requirement": "Must inform Data Protection Board of personal data breach",
                            "penalty": "Up to ₹250 crore"
                        },
                        "fix_steps": [
                            "Add reference to 'Data Protection Board of India'",
                            "Specify DPB notification timeline",
                            "Describe information shared with DPB",
                            "Include Hindi: डेटा संरक्षण बोर्ड"
                        ]
                    }
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
                visual_content = [
                    "VIOLATION: No DPO for Significant DF",
                    "",
                    "Indicators Found:",
                    "  Entity appears to be a Significant",
                    "  Data Fiduciary (large scale processing)",
                    "",
                    "Missing Requirement:",
                    "  ✗ Data Protection Officer (DPO)",
                    "",
                    "DPDP Section 10 - Mandatory for SDF",
                ]
                visual_box = generate_visual_box("DPO REQUIRED", visual_content)

                findings.append(Finding(
                    check_type=CheckType.OTHER,
                    severity=FindingSeverity.HIGH,
                    status=FindingStatus.FAIL,
                    title="No Data Protection Officer mentioned",
                    description="Entity appears to be a Significant Data Fiduciary but no DPO is mentioned. DPDP Section 10 requires SDFs to appoint a DPO.",
                    location=page.url,
                    dpdp_section=self.dpdp_section,
                    remediation="Appoint a Data Protection Officer and publish their contact details.",
                    extra_data={
                        "violation_type": "missing_dpo_sdf",
                        "sdf_indicators_found": [i for i in sdf_indicators if i in text_content],
                        "code_fix_example": '''
<section id="dpo">
  <h2>Data Protection Officer</h2>
  <p>As a Significant Data Fiduciary, we have appointed a
  Data Protection Officer to oversee data protection compliance.</p>

  <h3>DPO Contact Details</h3>
  <p><strong>Name:</strong> [DPO Name]</p>
  <p><strong>Email:</strong> dpo@company.com</p>
  <p><strong>Phone:</strong> +91-XXXXXXXXXX</p>
  <p><strong>Address:</strong> [Office Address]</p>

  <h3>DPO Responsibilities</h3>
  <ul>
    <li>Monitoring compliance with DPDP Act</li>
    <li>Advising on data protection matters</li>
    <li>Handling data subject requests</li>
    <li>Liaising with Data Protection Board</li>
  </ul>
</section>''',
                        "penalty_risk": "₹200 crore - DPDP Section 10 violation",
                        "visual_representation": visual_box,
                        "dpdp_reference": {
                            "section": "Section 10",
                            "requirement": "Significant Data Fiduciary must appoint a Data Protection Officer based in India",
                            "penalty": "Up to ₹200 crore"
                        },
                        "fix_steps": [
                            "Appoint a qualified Data Protection Officer",
                            "DPO must be based in India",
                            "Publish DPO contact details on website",
                            "Define DPO responsibilities clearly",
                            "Include Hindi: डेटा संरक्षण अधिकारी"
                        ]
                    }
                ))

            # Check for audit mention
            has_audit = any(keyword in text_content for keyword in self.AUDIT_KEYWORDS)

            if not has_audit:
                visual_content = [
                    "ISSUE: No Data Audit Mentioned",
                    "",
                    "For Significant Data Fiduciaries:",
                    "  Periodic data audits are required",
                    "",
                    "Missing References:",
                    "  ✗ Independent data audit",
                    "  ✗ Annual compliance audit",
                    "",
                    "DPDP Section 10 Requirement",
                ]
                visual_box = generate_visual_box("DATA AUDIT MISSING", visual_content)

                findings.append(Finding(
                    check_type=CheckType.OTHER,
                    severity=FindingSeverity.MEDIUM,
                    status=FindingStatus.FAIL,
                    title="No data audit information found",
                    description="Significant Data Fiduciary should conduct periodic data audits. No audit information found.",
                    location=page.url,
                    dpdp_section=self.dpdp_section,
                    remediation="Conduct and document periodic data protection audits by an independent auditor.",
                    extra_data={
                        "violation_type": "missing_data_audit",
                        "code_fix_example": '''
<section id="compliance-audit">
  <h2>Data Protection Audits</h2>
  <p>As a Significant Data Fiduciary, we conduct regular
  data protection audits to ensure compliance.</p>

  <h3>Audit Schedule</h3>
  <ul>
    <li>Annual comprehensive audit by independent auditor</li>
    <li>Quarterly internal compliance reviews</li>
    <li>Ad-hoc audits following incidents</li>
  </ul>

  <h3>Audit Scope</h3>
  <ul>
    <li>Data collection and processing practices</li>
    <li>Security measures and controls</li>
    <li>Consent management systems</li>
    <li>Data Principal rights fulfillment</li>
  </ul>

  <p>Audit reports are submitted to the Data Protection Board
  as required under DPDP Act.</p>
</section>''',
                        "penalty_risk": "₹50 crore - Incomplete SDF compliance",
                        "visual_representation": visual_box,
                        "dpdp_reference": {
                            "section": "Section 10",
                            "requirement": "Significant Data Fiduciary must conduct periodic data audits",
                            "penalty": "Up to ₹200 crore"
                        },
                        "fix_steps": [
                            "Engage independent data auditor",
                            "Conduct annual data protection audit",
                            "Document audit findings and remediation",
                            "Submit reports to DPB as required",
                            "Include Hindi: डेटा ऑडिट"
                        ]
                    }
                ))

        return findings

    def _is_privacy_page(self, url: str, text_content: str) -> bool:
        """Check if this is a privacy-related page."""
        url_lower = url.lower()

        if any(p in url_lower for p in ["privacy", "policy", "about", "compliance"]):
            return True

        return "privacy" in text_content[:1000]
