"""
DPDP GUI Compliance Scanner - Children's Data Detector

Detects compliance issues related to children's personal data per DPDP Section 9.
Based on Real-Time-Examples-Scenarios.md format for detailed findings.
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
            # Visual representation for children's data flow
            visual_content = [
                "CHILDREN'S DATA COMPLIANCE CHECK",
                "",
                "URL: Children-targeted content detected",
                "",
                "DETECTED FLOW:",
                "  Date of Birth: [NOT COLLECTED]",
                "                    ↓",
                "  ✗ NO AGE VERIFICATION",
                "  ✗ NO GUARDIAN CONSENT FLOW",
                "  ✗ DIRECT DATA COLLECTION",
                "",
                "DPDP Section 9 VIOLATIONS:",
                "• No verifiable age mechanism",
                "• No guardian identification",
                "• No separate consent for child's data",
                "",
                "PENALTY RISK: ₹200 crore",
            ]
            visual_box = generate_visual_box("MISSING AGE VERIFICATION", visual_content)

            # Required flow example
            required_flow = '''
REQUIRED CHILDREN'S DATA FLOW:
┌─────────────────────────────────────────┐
│  1. Detect age < 18 from DOB            │
│           ↓                              │
│  2. Prompt: "Guardian verification"     │
│           ↓                              │
│  3. Collect guardian's ID/Email         │
│           ↓                              │
│  4. OTP/Email verification to guardian  │
│           ↓                              │
│  5. Guardian consent checkbox           │
│     (NOT pre-selected)                  │
│           ↓                              │
│  6. Proceed with data collection        │
└─────────────────────────────────────────┘'''

            code_fix_example = '''
<!-- Age Verification Gate -->
<div class="age-gate">
  <h2>Please verify your age</h2>
  <label>Date of Birth:</label>
  <input type="date" id="dob" name="date_of_birth" required>
  <button onclick="verifyAge()">Verify Age</button>
</div>

<script>
function verifyAge() {
  const dob = new Date(document.getElementById('dob').value);
  const age = calculateAge(dob);
  if (age < 18) {
    showParentalConsentFlow();
  } else {
    proceedWithRegistration();
  }
}
</script>'''

            findings.append(Finding(
                check_type=CheckType.CHILDREN_AGE_VERIFICATION,
                severity=FindingSeverity.CRITICAL,
                status=FindingStatus.FAIL,
                title="No age verification mechanism found",
                description="This appears to be a children-targeted site but lacks age verification. DPDP Section 9 requires verification before processing children's data.",
                location=page.url,
                dpdp_section=self.dpdp_section,
                remediation="Implement a robust age verification mechanism (age gate, date of birth input) before collecting any personal data.",
                extra_data={
                    "violation_type": "missing_age_verification",
                    "children_indicators_found": [
                        ind for ind in self.CHILDREN_CONTENT_INDICATORS
                        if ind in text_content
                    ][:5],
                    "penalty_risk": "₹200 crore",
                    "visual_representation": visual_box,
                    "required_flow": required_flow,
                    "code_fix_example": code_fix_example,
                    "dpdp_reference": {
                        "section": "Section 9",
                        "requirement": "Before processing personal data of a child, obtain verifiable consent from parent/guardian",
                        "penalty": "Up to ₹200 crore"
                    },
                    "fix_steps": [
                        "Add date of birth field to registration",
                        "Calculate age and detect minors (< 18)",
                        "Trigger guardian verification flow for minors",
                        "Collect and verify parent/guardian contact",
                        "Send verification to guardian before proceeding",
                        "Require explicit guardian consent checkbox"
                    ]
                }
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
                # Visual representation
                visual_content = [
                    "PARENTAL CONSENT COMPLIANCE CHECK",
                    "",
                    "Current State:",
                    "  ✗ No parent/guardian email field",
                    "  ✗ No verifiable consent mechanism",
                    "  ✗ Direct data collection from minor",
                    "",
                    "Required per DPDP Section 9:",
                    "  ✓ Guardian identification",
                    "  ✓ Verifiable consent (email/SMS)",
                    "  ✓ Explicit consent checkbox",
                    "  ✓ Record of guardian consent",
                    "",
                    "PENALTY RISK: ₹200 crore",
                ]
                visual_box = generate_visual_box("MISSING PARENTAL CONSENT", visual_content)

                code_fix_example = '''
<!-- Parental Consent Section -->
<div class="parental-consent" id="guardian-section">
  <h3>Guardian Verification Required</h3>
  <p>Since you are under 18, we need your parent/guardian's consent.</p>

  <div class="form-group">
    <label>Parent/Guardian Name:</label>
    <input type="text" name="guardian_name" required>
  </div>

  <div class="form-group">
    <label>Parent/Guardian Email:</label>
    <input type="email" name="guardian_email" required>
  </div>

  <div class="form-group">
    <label>Relationship:</label>
    <select name="guardian_relationship">
      <option value="parent">Parent</option>
      <option value="guardian">Legal Guardian</option>
    </select>
  </div>

  <div class="form-check">
    <input type="checkbox" id="guardian-consent">
    <label>I confirm I am the parent/guardian and consent to
           my child's registration on this platform</label>
  </div>

  <button onclick="sendVerificationToGuardian()">
    Send Verification to Guardian
  </button>
</div>'''

                findings.append(Finding(
                    check_type=CheckType.CHILDREN_PARENTAL_CONSENT,
                    severity=FindingSeverity.CRITICAL,
                    status=FindingStatus.FAIL,
                    title="No parental consent mechanism found",
                    description="Children-targeted site collects data but lacks verifiable parental consent mechanism. DPDP Section 9 requires parental/guardian consent for processing children's data.",
                    location=page.url,
                    dpdp_section=self.dpdp_section,
                    remediation="Implement verifiable parental consent: parent email verification, signed consent form, or other approved methods.",
                    extra_data={
                        "violation_type": "missing_parental_consent",
                        "forms_count": len(soup.find_all("form")),
                        "penalty_risk": "₹200 crore",
                        "visual_representation": visual_box,
                        "code_fix_example": code_fix_example,
                        "dpdp_reference": {
                            "section": "Section 9",
                            "requirement": "Verifiable consent from parent/guardian required for children's data",
                            "penalty": "Up to ₹200 crore"
                        },
                        "verification_methods": [
                            "Parent/Guardian email verification with OTP",
                            "SMS verification to guardian mobile",
                            "Signed digital consent form",
                            "Video KYC verification of guardian",
                            "Guardian's government ID verification"
                        ],
                        "fix_steps": [
                            "Add guardian information fields (name, email, mobile)",
                            "Add relationship selector (parent/legal guardian)",
                            "Send verification OTP/link to guardian",
                            "Add explicit consent checkbox for guardian",
                            "Store consent record with timestamp",
                            "Allow guardian to withdraw consent"
                        ]
                    }
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
            all_tracking = tracking_found + tracking_scripts

            # Visual representation
            visual_content = [
                "PROHIBITED TRACKING ON CHILDREN'S SITE",
                "",
                "DPDP Section 9 PROHIBITION:",
                "No tracking, behavioral monitoring, or",
                "targeted advertising for children.",
                "",
                "TRACKING DETECTED:",
            ]
            for tracker in all_tracking[:5]:
                visual_content.append(f"  ✗ {tracker}")

            visual_content.extend([
                "",
                "These MUST be removed for compliance.",
                "",
                "PENALTY RISK: ₹200 crore",
            ])
            visual_box = generate_visual_box("TRACKING ON CHILDREN'S SITE", visual_content)

            findings.append(Finding(
                check_type=CheckType.OTHER,
                severity=FindingSeverity.CRITICAL,
                status=FindingStatus.FAIL,
                title="Tracking/behavioral advertising detected on children's site",
                description=f"DPDP Section 9 prohibits tracking, behavioral monitoring, and targeted advertising for children. Found: {', '.join(all_tracking)[:200]}",
                location=page.url,
                dpdp_section=self.dpdp_section,
                remediation="Remove all tracking, analytics, and behavioral advertising from children-targeted sections. Only essential cookies should be used.",
                extra_data={
                    "violation_type": "children_tracking_prohibited",
                    "trackers_found": all_tracking,
                    "tracking_scripts": tracking_scripts,
                    "tracking_text": tracking_found,
                    "penalty_risk": "₹200 crore",
                    "visual_representation": visual_box,
                    "dpdp_reference": {
                        "section": "Section 9(3)",
                        "requirement": "No tracking, behavioral monitoring, or targeted advertising for children",
                        "penalty": "Up to ₹200 crore"
                    },
                    "fix_steps": [
                        "Remove Google Analytics from children's pages",
                        "Remove Facebook Pixel and other ad trackers",
                        "Disable personalized advertising",
                        "Use privacy-focused analytics (if needed)",
                        "Implement age-gated tracking (disable for minors)",
                        "Only use essential/functional cookies"
                    ],
                    "scripts_to_remove": [
                        "google-analytics.com/analytics.js",
                        "googletagmanager.com/gtag/js",
                        "connect.facebook.net/en_US/fbevents.js",
                        "static.ads-twitter.com/uwt.js",
                        "All ad network scripts"
                    ]
                }
            ))

        # Check for third-party cookies mention without exception for children
        cookie_text = text_content
        if "third party" in cookie_text and "cookie" in cookie_text:
            if not any(term in cookie_text for term in ["except children", "not for children", "disable for minors"]):
                visual_content = [
                    "THIRD-PARTY DATA SHARING ON CHILDREN'S SITE",
                    "",
                    "Issue:",
                    "  Third-party cookies/data sharing detected",
                    "  No exemption for children mentioned",
                    "",
                    "DPDP Section 9 Requirement:",
                    "  Children's data must not be shared",
                    "  for tracking or advertising purposes",
                    "",
                    "PENALTY RISK: ₹200 crore",
                ]
                visual_box = generate_visual_box("THIRD-PARTY SHARING ISSUE", visual_content)

                findings.append(Finding(
                    check_type=CheckType.OTHER,
                    severity=FindingSeverity.HIGH,
                    status=FindingStatus.FAIL,
                    title="Third-party data sharing on children's site",
                    description="Third-party cookies/data sharing detected without explicit exemption for children's data.",
                    location=page.url,
                    dpdp_section=self.dpdp_section,
                    remediation="Disable third-party data sharing for users identified as children. Implement age-gated cookie consent.",
                    extra_data={
                        "violation_type": "children_third_party_sharing",
                        "penalty_risk": "₹200 crore",
                        "visual_representation": visual_box,
                        "code_fix_example": '''
<!-- Age-gated cookie consent -->
<script>
function setCookiePreferences(userAge) {
  if (userAge < 18) {
    // Disable all non-essential cookies for children
    disableAnalytics();
    disableAdvertising();
    disableThirdPartyCookies();
    console.log('Third-party cookies disabled for minor user');
  } else {
    showCookieConsentBanner();
  }
}
</script>

<!-- Cookie policy update -->
<p><strong>Children's Privacy:</strong>
We do not use third-party cookies or share data
with advertising networks for users under 18.</p>''',
                        "dpdp_reference": {
                            "section": "Section 9",
                            "requirement": "No data sharing for tracking/advertising purposes for children",
                            "penalty": "Up to ₹200 crore"
                        },
                        "fix_steps": [
                            "Implement age detection in cookie consent flow",
                            "Disable third-party cookies for users under 18",
                            "Add explicit exemption for children in privacy policy",
                            "Block advertising network scripts for minors"
                        ]
                    }
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
                    visual_content = [
                        "AGE COLLECTION WITHOUT CHILDREN NOTICE",
                        "",
                        "Issue:",
                        "  Form collects age/DOB",
                        "  No mention of children's data handling",
                        "",
                        "Required Notice:",
                        "  ✗ What happens if user is under 18",
                        "  ✗ Parental consent requirements",
                        "  ✗ Different data handling for minors",
                        "",
                        "DPDP Section 9 Compliance",
                    ]
                    visual_box = generate_visual_box("MISSING CHILDREN'S NOTICE", visual_content)

                    findings.append(Finding(
                        check_type=CheckType.CHILDREN_DOB_FIELD,
                        severity=FindingSeverity.MEDIUM,
                        status=FindingStatus.FAIL,
                        title="Age collection without children's data handling notice",
                        description="Form collects age/date of birth but doesn't explain how children's data will be handled differently.",
                        location=page.url,
                        element_selector=str(form)[:500],
                        dpdp_section=self.dpdp_section,
                        remediation="Add clear notice about how data will be handled if user is under 18, including parental consent requirements.",
                        extra_data={
                            "violation_type": "missing_children_notice",
                            "age_fields_found": [str(f.get("name", "unnamed")) for f in age_fields],
                            "penalty_risk": "₹50 crore",
                            "visual_representation": visual_box,
                            "code_fix_example": '''
<!-- Add children's data notice near DOB field -->
<div class="form-group">
  <label for="dob">Date of Birth *</label>
  <input type="date" id="dob" name="date_of_birth" required>

  <div class="children-notice">
    <small>
      <strong>Important:</strong> If you are under 18 years of age,
      we will require your parent/guardian's consent before processing
      your data. Your guardian will be contacted for verification.
      <a href="/privacy-policy#children">Learn more about children's privacy</a>
    </small>
  </div>
</div>

<!-- Hindi version -->
<small lang="hi">
  <strong>महत्वपूर्ण:</strong> यदि आप 18 वर्ष से कम आयु के हैं,
  तो हमें आपके माता-पिता/अभिभावक की सहमति की आवश्यकता होगी।
</small>''',
                            "dpdp_reference": {
                                "section": "Section 9",
                                "requirement": "Transparency about children's data processing",
                                "penalty": "Up to ₹200 crore"
                            },
                            "fix_steps": [
                                "Add notice near age/DOB input field",
                                "Explain what happens if user is under 18",
                                "Mention parental consent requirement",
                                "Link to children's privacy section",
                                "Add Hindi translation for Indian users"
                            ]
                        }
                    ))

        return findings
