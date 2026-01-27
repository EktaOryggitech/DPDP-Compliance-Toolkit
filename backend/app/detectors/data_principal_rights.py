"""
DPDP GUI Compliance Scanner - Data Principal Rights Detector

Detects compliance issues related to Data Principal rights per DPDP Section 11-14.
"""
import re
from typing import List, Dict, Any
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
            visual_content = [
                "VIOLATION: Missing Data Access Mechanism",
                "",
                "DPDP Section 11 - Right to Access",
                "",
                "Required Elements (NOT FOUND):",
                "  ✗ How to request data access",
                "  ✗ Timeline for response",
                "  ✗ Format of data provided",
                "  ✗ Process description",
                "",
                "Penalty: Up to ₹200 crore",
            ]
            visual_box = generate_visual_box("DATA ACCESS RIGHT MISSING", visual_content)

            findings.append(Finding(
                check_type=CheckType.RIGHTS_ACCESS,
                severity=FindingSeverity.HIGH,
                status=FindingStatus.FAIL,
                title="No data access mechanism described",
                description="Privacy policy does not describe how users can access their personal data. DPDP Section 11 requires providing access to personal data upon request.",
                location=page.url,
                dpdp_section="Section 11",
                remediation="Add clear information about how users can request and obtain a copy of their personal data, including the process and timeline.",
                extra_data={
                    "violation_type": "missing_access_right",
                    "keywords_searched": self.ACCESS_RIGHTS_KEYWORDS[:5],
                    "code_fix_example": '''
<section id="data-access">
  <h2>Right to Access Your Data (Section 11)</h2>
  <p>You have the right to:</p>
  <ul>
    <li>Request a summary of your personal data</li>
    <li>Know the processing activities</li>
    <li>Obtain identities of other Data Fiduciaries with whom data was shared</li>
  </ul>
  <h3>How to Request</h3>
  <ol>
    <li>Email: dataaccess@company.com</li>
    <li>Use our online form: <a href="/data-access-request">Request Form</a></li>
  </ol>
  <p>Response time: Within 72 hours of identity verification</p>
</section>''',
                    "penalty_risk": "₹200 crore - DPDP Section 11 violation",
                    "visual_representation": visual_box,
                    "dpdp_reference": {
                        "section": "Section 11",
                        "requirement": "Data Principal has right to obtain summary of personal data and processing activities",
                        "penalty": "Up to ₹200 crore"
                    },
                    "fix_steps": [
                        "Add 'Right to Access' section in privacy policy",
                        "Create online data access request form",
                        "Specify response timeline (recommended: 72 hours)",
                        "Describe format of data provided (JSON, PDF, etc.)",
                        "Include Hindi version: डेटा एक्सेस का अधिकार"
                    ]
                }
            ))

        return findings

    def _check_correction_rights(self, text_content: str, page: CrawledPage) -> List[Finding]:
        """Check for Section 12 - Right to correction."""
        findings = []

        has_correction_info = any(
            keyword in text_content for keyword in self.CORRECTION_KEYWORDS
        )

        if not has_correction_info:
            visual_content = [
                "VIOLATION: Missing Data Correction Mechanism",
                "",
                "DPDP Section 12 - Right to Correction",
                "",
                "Required Elements (NOT FOUND):",
                "  ✗ How to request data correction",
                "  ✗ Self-service profile editing",
                "  ✗ Process for disputed corrections",
                "",
                "Penalty: Up to ₹200 crore",
            ]
            visual_box = generate_visual_box("DATA CORRECTION RIGHT MISSING", visual_content)

            findings.append(Finding(
                check_type=CheckType.RIGHTS_CORRECTION,
                severity=FindingSeverity.HIGH,
                status=FindingStatus.FAIL,
                title="No data correction mechanism described",
                description="Privacy policy does not describe how users can correct/update their personal data. DPDP Section 12 requires allowing correction of inaccurate data.",
                location=page.url,
                dpdp_section="Section 12",
                remediation="Add information about how users can request correction of inaccurate or incomplete personal data.",
                extra_data={
                    "violation_type": "missing_correction_right",
                    "keywords_searched": self.CORRECTION_KEYWORDS[:5],
                    "code_fix_example": '''
<section id="data-correction">
  <h2>Right to Correction (Section 12)</h2>
  <p>You have the right to correct inaccurate or incomplete personal data.</p>

  <h3>Self-Service Correction</h3>
  <p>Update your profile directly: <a href="/profile/edit">Edit Profile</a></p>

  <h3>Request Correction</h3>
  <p>For data you cannot edit yourself:</p>
  <ol>
    <li>Email: correction@company.com</li>
    <li>Specify the data to be corrected</li>
    <li>Provide supporting documentation if needed</li>
  </ol>
  <p>Response time: Within 15 days</p>
</section>''',
                    "penalty_risk": "₹200 crore - DPDP Section 12 violation",
                    "visual_representation": visual_box,
                    "dpdp_reference": {
                        "section": "Section 12",
                        "requirement": "Data Principal has right to correction of inaccurate or misleading personal data",
                        "penalty": "Up to ₹200 crore"
                    },
                    "fix_steps": [
                        "Add 'Right to Correction' section in privacy policy",
                        "Provide self-service profile editing feature",
                        "Create correction request process for non-editable data",
                        "Specify response timeline",
                        "Include Hindi version: डेटा सुधार का अधिकार"
                    ]
                }
            ))

        return findings

    def _check_erasure_rights(self, text_content: str, page: CrawledPage) -> List[Finding]:
        """Check for Section 12 - Right to erasure."""
        findings = []

        has_erasure_info = any(
            keyword in text_content for keyword in self.ERASURE_KEYWORDS
        )

        if not has_erasure_info:
            visual_content = [
                "VIOLATION: Missing Data Erasure Mechanism",
                "",
                "DPDP Section 12 - Right to Erasure",
                "",
                "Required Elements (NOT FOUND):",
                "  ✗ Account deletion option",
                "  ✗ Data deletion request process",
                "  ✗ Deletion confirmation mechanism",
                "",
                "Penalty: Up to ₹200 crore",
            ]
            visual_box = generate_visual_box("DATA ERASURE RIGHT MISSING", visual_content)

            findings.append(Finding(
                check_type=CheckType.RIGHTS_ERASURE,
                severity=FindingSeverity.HIGH,
                status=FindingStatus.FAIL,
                title="No data deletion mechanism described",
                description="Privacy policy does not describe how users can delete their personal data. DPDP Section 12 requires allowing erasure when data is no longer needed.",
                location=page.url,
                dpdp_section="Section 12",
                remediation="Add clear information about how users can request deletion of their personal data and account.",
                extra_data={
                    "violation_type": "missing_erasure_right",
                    "keywords_searched": self.ERASURE_KEYWORDS[:5],
                    "code_fix_example": '''
<section id="data-deletion">
  <h2>Right to Erasure (Section 12)</h2>
  <p>You have the right to request deletion of your personal data when:</p>
  <ul>
    <li>Data is no longer needed for the original purpose</li>
    <li>You withdraw consent</li>
    <li>Data has been unlawfully processed</li>
  </ul>

  <h3>How to Request Deletion</h3>
  <a href="/account/delete" class="btn btn-danger">Delete My Account</a>
  <p>Or email: deletion@company.com</p>

  <h3>What Happens Next</h3>
  <ol>
    <li>Identity verification (24 hours)</li>
    <li>Data deletion process (7 days)</li>
    <li>Confirmation email sent</li>
  </ol>
</section>''',
                    "penalty_risk": "₹200 crore - DPDP Section 12 violation",
                    "visual_representation": visual_box,
                    "dpdp_reference": {
                        "section": "Section 12",
                        "requirement": "Data Principal has right to erasure of personal data",
                        "penalty": "Up to ₹200 crore"
                    },
                    "fix_steps": [
                        "Add 'Delete Account' option in settings",
                        "Create data deletion request process",
                        "Specify deletion timeline and confirmation",
                        "Explain any data retention exceptions (legal requirements)",
                        "Include Hindi version: डेटा विलोपन का अधिकार"
                    ]
                }
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
            visual_content = [
                "CRITICAL: No Grievance Mechanism Found",
                "",
                "DPDP Section 13 - Mandatory Requirement",
                "",
                "Required Elements (NOT FOUND):",
                "  ✗ Grievance Officer designation",
                "  ✗ Contact details (email/phone)",
                "  ✗ Complaint submission process",
                "  ✗ Response timeline",
                "",
                "Penalty: Up to ₹250 crore",
            ]
            visual_box = generate_visual_box("GRIEVANCE MECHANISM MISSING", visual_content)

            findings.append(Finding(
                check_type=CheckType.RIGHTS_GRIEVANCE,
                severity=FindingSeverity.CRITICAL,
                status=FindingStatus.FAIL,
                title="No grievance redressal mechanism found",
                description="No grievance officer or complaint mechanism described. DPDP Section 13 mandates a grievance redressal mechanism.",
                location=page.url,
                dpdp_section="Section 13",
                remediation="Appoint a Grievance Officer and publish their name, contact details, and the grievance submission process.",
                extra_data={
                    "violation_type": "missing_grievance_mechanism",
                    "keywords_searched": self.GRIEVANCE_KEYWORDS[:5],
                    "code_fix_example": '''
<section id="grievance">
  <h2>Grievance Redressal (Section 13)</h2>

  <h3>Grievance Officer</h3>
  <p><strong>Name:</strong> [Officer Name]</p>
  <p><strong>Designation:</strong> Data Protection Officer</p>
  <p><strong>Email:</strong> grievance@company.com</p>
  <p><strong>Phone:</strong> +91-XXXXXXXXXX</p>
  <p><strong>Address:</strong> [Office Address]</p>

  <h3>How to File a Grievance</h3>
  <ol>
    <li>Email your concern to grievance@company.com</li>
    <li>Include your registered email and description</li>
    <li>Receive acknowledgment within 24 hours</li>
    <li>Resolution within 7 days</li>
  </ol>

  <a href="/grievance/submit" class="btn">Submit Grievance</a>
</section>''',
                    "penalty_risk": "₹250 crore - DPDP Section 13 violation (CRITICAL)",
                    "visual_representation": visual_box,
                    "dpdp_reference": {
                        "section": "Section 13",
                        "requirement": "Data Fiduciary must have grievance redressal mechanism and respond within prescribed time",
                        "penalty": "Up to ₹250 crore"
                    },
                    "fix_steps": [
                        "Appoint a Grievance Officer immediately",
                        "Publish officer name and contact details",
                        "Create grievance submission form/process",
                        "Set up tracking system for complaints",
                        "Ensure response within 7 days (DPDP requirement)",
                        "Include Hindi: शिकायत निवारण अधिकारी"
                    ]
                }
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
            visual_content = [
                "INCOMPLETE: Grievance Officer Details",
                "",
                "Found: Grievance mechanism mentioned",
                "",
                "Missing Elements:",
            ]
            for m in missing:
                visual_content.append(f"  ✗ {m}")
            visual_content.extend([
                "",
                "DPDP Section 13 - Complete details required",
                "Response timeline: 7 days mandatory",
            ])
            visual_box = generate_visual_box("INCOMPLETE GRIEVANCE DETAILS", visual_content)

            findings.append(Finding(
                check_type=CheckType.RIGHTS_GRIEVANCE,
                severity=FindingSeverity.MEDIUM,
                status=FindingStatus.FAIL,
                title="Incomplete grievance officer details",
                description=f"Grievance mechanism mentioned but missing: {', '.join(missing)}. Complete contact details are required.",
                location=page.url,
                dpdp_section="Section 13",
                remediation=f"Add the following to grievance section: {', '.join(missing)}. Response should be within 7 days as per DPDP.",
                extra_data={
                    "violation_type": "incomplete_grievance_details",
                    "missing_elements": missing,
                    "has_email": has_email,
                    "has_phone": has_phone,
                    "has_name": has_name,
                    "has_timeline": has_timeline,
                    "code_fix_example": '''
<div class="grievance-officer">
  <h3>Grievance Officer Details</h3>
  <p><strong>Name:</strong> Mr./Ms. [Full Name]</p>
  <p><strong>Designation:</strong> Grievance Officer / DPO</p>
  <p><strong>Email:</strong> grievance@company.com</p>
  <p><strong>Phone:</strong> +91-XXXXXXXXXX</p>
  <p><strong>Response Time:</strong> Within 7 days of receiving complaint</p>
</div>''',
                    "penalty_risk": "₹50 crore - DPDP Section 13 partial violation",
                    "visual_representation": visual_box,
                    "dpdp_reference": {
                        "section": "Section 13",
                        "requirement": "Complete grievance officer details with response timeline",
                        "penalty": "Up to ₹250 crore"
                    },
                    "fix_steps": [f"Add {m}" for m in missing] + [
                        "Ensure 7-day response timeline is mentioned",
                        "Provide multiple contact methods (email + phone)"
                    ]
                }
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
            visual_content = [
                "MISSING: Nomination Provision",
                "",
                "DPDP Section 14 - Right to Nominate",
                "",
                "Data Principal can nominate another person",
                "to exercise rights in case of:",
                "  • Death of Data Principal",
                "  • Incapacity of Data Principal",
                "",
                "This is a recommended practice",
            ]
            visual_box = generate_visual_box("NOMINATION PROVISION MISSING", visual_content)

            findings.append(Finding(
                check_type=CheckType.RIGHTS_NOMINATION,
                severity=FindingSeverity.LOW,
                status=FindingStatus.FAIL,
                title="No nomination provision described",
                description="Privacy policy describes data rights but doesn't mention nomination of another person to exercise rights (in case of death/incapacity). DPDP Section 14 allows for nomination.",
                location=page.url,
                dpdp_section="Section 14",
                remediation="Add information about how users can nominate someone to exercise their data rights in case of death or incapacity.",
                extra_data={
                    "violation_type": "missing_nomination_provision",
                    "keywords_searched": self.NOMINATION_KEYWORDS[:5],
                    "code_fix_example": '''
<section id="nomination">
  <h2>Right to Nominate (Section 14)</h2>
  <p>You can nominate another person to exercise your data rights
  in case of your death or incapacity.</p>

  <h3>How to Nominate</h3>
  <ol>
    <li>Go to Account Settings → Nomination</li>
    <li>Add nominee details (name, relationship, contact)</li>
    <li>Nominee will need to verify identity to exercise rights</li>
  </ol>

  <a href="/settings/nomination" class="btn">Add Nominee</a>

  <h3>What Can Nominee Do?</h3>
  <ul>
    <li>Access your personal data</li>
    <li>Request correction or deletion</li>
    <li>Exercise all Data Principal rights on your behalf</li>
  </ul>
</section>''',
                    "penalty_risk": "₹10 crore - DPDP Section 14 (lower severity)",
                    "visual_representation": visual_box,
                    "dpdp_reference": {
                        "section": "Section 14",
                        "requirement": "Data Principal may nominate another to exercise rights in case of death/incapacity",
                        "penalty": "Up to ₹50 crore"
                    },
                    "fix_steps": [
                        "Add 'Nomination' section in privacy policy",
                        "Create nomination feature in account settings",
                        "Specify what rights nominee can exercise",
                        "Include verification process for nominee",
                        "Include Hindi: नामांकन का अधिकार"
                    ]
                }
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
            visual_content = [
                "VIOLATION: No Data Retention Policy",
                "",
                "DPDP Section 8 - Data Retention",
                "",
                "Required Information (NOT FOUND):",
                "  ✗ How long data is kept",
                "  ✗ Retention criteria",
                "  ✗ Deletion timeline after purpose fulfilled",
                "",
                "Penalty: Up to ₹50 crore",
            ]
            visual_box = generate_visual_box("DATA RETENTION POLICY MISSING", visual_content)

            findings.append(Finding(
                check_type=CheckType.OTHER,
                severity=FindingSeverity.MEDIUM,
                status=FindingStatus.FAIL,
                title="No data retention policy found",
                description="Privacy policy does not describe how long personal data is retained. DPDP requires data to be deleted when no longer needed for the stated purpose.",
                location=page.url,
                dpdp_section=self.dpdp_section,
                remediation="Add clear information about data retention periods for each type of data collected and the criteria for determining retention.",
                extra_data={
                    "violation_type": "missing_retention_policy",
                    "keywords_searched": self.RETENTION_KEYWORDS[:5],
                    "code_fix_example": '''
<section id="data-retention">
  <h2>Data Retention Policy</h2>

  <table>
    <tr>
      <th>Data Type</th>
      <th>Retention Period</th>
      <th>Reason</th>
    </tr>
    <tr>
      <td>Account Information</td>
      <td>Until account deletion + 30 days</td>
      <td>Service provision</td>
    </tr>
    <tr>
      <td>Transaction Records</td>
      <td>7 years</td>
      <td>Legal/tax requirements</td>
    </tr>
    <tr>
      <td>Usage Logs</td>
      <td>90 days</td>
      <td>Security and analytics</td>
    </tr>
    <tr>
      <td>Marketing Preferences</td>
      <td>Until consent withdrawn</td>
      <td>Marketing communications</td>
    </tr>
  </table>

  <p>Data is securely deleted after retention period expires.</p>
</section>''',
                    "penalty_risk": "₹50 crore - DPDP Section 8 violation",
                    "visual_representation": visual_box,
                    "dpdp_reference": {
                        "section": "Section 8",
                        "requirement": "Personal data shall be erased when no longer necessary for the purpose",
                        "penalty": "Up to ₹50 crore"
                    },
                    "fix_steps": [
                        "Add 'Data Retention' section in privacy policy",
                        "Specify retention period for each data category",
                        "Explain legal basis for retention",
                        "Describe secure deletion process",
                        "Include Hindi: डेटा प्रतिधारण नीति"
                    ]
                }
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
                visual_content = [
                    "ISSUE: Vague Retention Period",
                    "",
                    "Found: Retention policy exists",
                    "Problem: No specific time periods",
                    "",
                    "Vague phrases detected:",
                    "  ✗ 'as long as necessary'",
                    "  ✗ 'reasonable period'",
                    "  ✗ 'until no longer needed'",
                    "",
                    "Required: Specific periods (e.g., '2 years')",
                ]
                visual_box = generate_visual_box("VAGUE RETENTION PERIOD", visual_content)

                findings.append(Finding(
                    check_type=CheckType.OTHER,
                    severity=FindingSeverity.LOW,
                    status=FindingStatus.FAIL,
                    title="Data retention period not specific",
                    description="Retention policy mentioned but no specific time periods given. Vague language like 'as long as necessary' is insufficient.",
                    location=page.url,
                    dpdp_section=self.dpdp_section,
                    remediation="Specify exact retention periods (e.g., '2 years from last activity') rather than vague statements.",
                    extra_data={
                        "violation_type": "vague_retention_period",
                        "code_before": '''
<!-- Vague retention language (BAD) -->
<p>We retain your data as long as necessary for the purposes
described in this policy.</p>''',
                        "code_after": '''
<!-- Specific retention periods (GOOD) -->
<p>We retain your data for the following periods:</p>
<ul>
  <li>Account data: Duration of account + 30 days</li>
  <li>Transaction history: 7 years (legal requirement)</li>
  <li>Support tickets: 2 years from resolution</li>
  <li>Marketing data: Until consent withdrawn</li>
</ul>''',
                        "penalty_risk": "₹10 crore - Best practice violation",
                        "visual_representation": visual_box,
                        "dpdp_reference": {
                            "section": "Section 8",
                            "requirement": "Clear retention periods for transparency",
                            "penalty": "Up to ₹50 crore"
                        },
                        "fix_steps": [
                            "Replace vague language with specific periods",
                            "Use format: 'X years/months/days'",
                            "Specify trigger (e.g., 'from last activity')",
                            "Create retention schedule table"
                        ]
                    }
                ))

        return findings

    def _is_privacy_page(self, url: str, text_content: str) -> bool:
        """Check if this is a privacy-related page."""
        url_lower = url.lower()

        if any(p in url_lower for p in ["privacy", "policy", "terms", "data"]):
            return True

        return "privacy" in text_content[:1000] or "personal data" in text_content[:1000]
