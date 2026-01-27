"""
DPDP GUI Compliance Scanner - Consent Mechanism Detector

Detects consent mechanism compliance issues per DPDP Section 6.
Based on Real-Time-Examples-Scenarios.md format for detailed findings.
"""
import re
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup, Tag

from app.detectors.base import BaseDetector
from app.models.finding import CheckType, Finding, FindingSeverity, FindingStatus
from app.scanners.web.crawler import CrawledPage


def get_element_html(element: Tag, max_length: int = 300) -> str:
    """Extract clean HTML from element for display."""
    html = str(element)
    html = re.sub(r'\s+', ' ', html)
    return html[:max_length] + "..." if len(html) > max_length else html


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


class ConsentDetector(BaseDetector):
    """
    Detector for DPDP Section 6 - Consent Requirements.

    Checks for:
    - Free, specific, informed, unconditional, unambiguous consent
    - Granular consent options
    - Pre-checked checkboxes (violation)
    - Consent withdrawal mechanisms
    - Record of consent
    """

    dpdp_section = "Section 6"
    description = "Detects consent mechanism compliance issues"

    # Keywords for consent-related elements
    CONSENT_KEYWORDS = [
        "consent", "agree", "accept", "i agree", "i consent",
        "सहमति", "स्वीकार", "मैं सहमत हूं",
    ]

    async def detect(self, page: CrawledPage) -> List[Finding]:
        """Detect consent mechanism issues on the page."""
        findings = []

        soup = BeautifulSoup(page.html_content, "html.parser")

        # Check for pre-checked consent checkboxes
        prechecked = self._detect_prechecked_consent(soup, page)
        findings.extend(prechecked)

        # Check for bundled consent
        bundled = self._detect_bundled_consent(soup, page)
        findings.extend(bundled)

        # Check for hidden consent
        hidden = self._detect_hidden_consent(soup, page)
        findings.extend(hidden)

        # Check consent withdrawal mechanism
        withdrawal = self._detect_withdrawal_issues(soup, page)
        findings.extend(withdrawal)

        # Check cookie consent
        cookie_findings = self._detect_cookie_consent_issues(page)
        findings.extend(cookie_findings)

        return findings

    def _detect_prechecked_consent(self, soup: BeautifulSoup, page: CrawledPage) -> List[Finding]:
        """Detect pre-checked consent checkboxes."""
        findings = []

        checkboxes = soup.find_all("input", {"type": "checkbox"})

        for cb in checkboxes:
            # Get associated label text
            label_text = ""
            label_id = cb.get("id")

            if label_id:
                label = soup.find("label", {"for": label_id})
                if label:
                    label_text = label.get_text().lower()

            # Also check parent text
            parent_text = cb.parent.get_text().lower() if cb.parent else ""
            combined_text = label_text + " " + parent_text

            # Check if consent-related
            is_consent = any(kw in combined_text for kw in self.CONSENT_KEYWORDS)

            if is_consent:
                # Check if pre-checked
                is_checked = cb.has_attr("checked")

                if is_checked:
                    # Get element HTML for code_before
                    element_html = get_element_html(cb)
                    display_text = label_text[:100] or parent_text[:100]

                    # Generate code_before and code_after
                    code_before = f'<input type="checkbox" id="{label_id}" checked>'
                    code_after = f'<input type="checkbox" id="{label_id}">'

                    # Visual representation matching Real-Time-Examples format
                    visual_content = [
                        "VIOLATION DETECTED: Pre-Selected Consent",
                        "",
                        f"Location: {page.url[:40]}...",
                        f"Element: {element_html[:50]}...",
                        "",
                        "  ┌─────────────────────────────────────┐",
                        f"  │  ☑ {display_text[:35]}... │",
                        "  └─────────────────────────────────────┘",
                        "       ↑",
                        "       └── VIOLATION: Checkbox is pre-checked",
                        "",
                        "DPDP Section 6(1) - Consent must be freely given",
                        "Penalty Risk: ₹50 crore",
                    ]
                    visual_box = generate_visual_box("PRE-SELECTED CONSENT", visual_content)

                    findings.append(Finding(
                        check_type=CheckType.DARK_PATTERN_PRESELECTED,
                        severity=FindingSeverity.CRITICAL,
                        status=FindingStatus.FAIL,
                        title="Pre-checked consent checkbox detected",
                        description=f"A consent checkbox is pre-checked by default. Text: '{display_text}'. This violates DPDP requirement for explicit, affirmative consent.",
                        location=page.url,
                        element_selector=f"input[id='{label_id}']" if label_id else "input[type='checkbox']",
                        dpdp_section=self.dpdp_section,
                        remediation="Remove the 'checked' attribute from consent checkboxes. Users must explicitly opt-in.",
                        extra_data={
                            "violation_type": "pre_selected_consent",
                            "element_id": label_id,
                            "consent_text": display_text,
                            "code_before": code_before,
                            "code_after": code_after,
                            "penalty_risk": "₹50 crore",
                            "visual_representation": visual_box,
                            "dpdp_reference": {
                                "section": "Section 6(1)",
                                "requirement": "Consent must be free, specific, informed, unconditional, and unambiguous with clear affirmative action",
                                "penalty": "Up to ₹50 crore"
                            },
                            "fix_steps": [
                                'Remove "checked" attribute from checkbox',
                                "Require explicit user action to provide consent",
                                "Add clear description of what data is shared",
                                "Ensure checkbox is unchecked by default"
                            ],
                            "code_fix": {
                                "before": code_before,
                                "after": code_after,
                                "explanation": 'Remove the "checked" attribute to require explicit user consent'
                            }
                        }
                    ))

        return findings

    def _detect_bundled_consent(self, soup: BeautifulSoup, page: CrawledPage) -> List[Finding]:
        """Detect bundled/combined consent (multiple purposes in one checkbox)."""
        findings = []

        checkboxes = soup.find_all("input", {"type": "checkbox"})

        # Keywords that indicate different consent purposes
        purpose_groups = [
            ["marketing", "promotional", "newsletter", "offers"],
            ["analytics", "tracking", "statistics"],
            ["third party", "partner", "share"],
            ["personalization", "recommendations"],
        ]

        for cb in checkboxes:
            label_text = ""
            label_id = cb.get("id")

            if label_id:
                label = soup.find("label", {"for": label_id})
                if label:
                    label_text = label.get_text().lower()

            parent_text = cb.parent.get_text().lower() if cb.parent else ""
            combined_text = label_text + " " + parent_text

            # Count how many purpose groups are mentioned
            matched_groups = 0
            matched_purposes = []

            for group in purpose_groups:
                if any(kw in combined_text for kw in group):
                    matched_groups += 1
                    matched_purposes.extend([kw for kw in group if kw in combined_text])

            if matched_groups >= 2:
                # Visual representation
                visual_content = [
                    "VIOLATION: BUNDLED CONSENT",
                    "",
                    "Single checkbox contains multiple purposes:",
                    f"  • {', '.join(matched_purposes[:3])}",
                    "",
                    "Current (INCORRECT):",
                    "  ☐ I agree to marketing, analytics, and",
                    "    third-party data sharing",
                    "",
                    "Required (CORRECT):",
                    "  ☐ I agree to receive marketing emails",
                    "  ☐ I agree to analytics tracking",
                    "  ☐ I agree to share data with partners",
                    "",
                    "DPDP Section 6 - Granular consent required",
                ]
                visual_box = generate_visual_box("BUNDLED CONSENT", visual_content)

                # Generate separate consent code example
                code_fix_example = '''
<!-- BEFORE: Bundled consent -->
<input type="checkbox" id="consent-all">
<label>I agree to marketing, analytics, and third-party sharing</label>

<!-- AFTER: Granular consent -->
<div class="consent-group">
  <input type="checkbox" id="consent-marketing">
  <label>I agree to receive marketing emails</label>
</div>
<div class="consent-group">
  <input type="checkbox" id="consent-analytics">
  <label>I agree to analytics tracking</label>
</div>
<div class="consent-group">
  <input type="checkbox" id="consent-partners">
  <label>I agree to share data with partners</label>
</div>'''

                findings.append(Finding(
                    check_type=CheckType.CONSENT_GRANULAR,
                    severity=FindingSeverity.HIGH,
                    status=FindingStatus.FAIL,
                    title="Bundled consent detected",
                    description=f"A single checkbox combines multiple consent purposes: {', '.join(matched_purposes[:5])}. DPDP requires granular consent for each purpose.",
                    location=page.url,
                    element_selector=f"input[id='{label_id}']" if label_id else None,
                    dpdp_section=self.dpdp_section,
                    remediation="Separate different consent purposes into individual checkboxes. Users should be able to consent to each purpose independently.",
                    extra_data={
                        "violation_type": "bundled_consent",
                        "purposes_detected": matched_purposes,
                        "purpose_count": matched_groups,
                        "consent_text": combined_text[:200],
                        "penalty_risk": "₹50 crore - DPDP Section 6(4) violation",
                        "visual_representation": visual_box,
                        "code_fix_example": code_fix_example,
                        "dpdp_reference": {
                            "section": "Section 6(4)",
                            "requirement": "Consent must not be conditional on performance of contract if not necessary for the stated purpose",
                            "penalty": "Up to ₹50 crore"
                        },
                        "fix_steps": [
                            "Identify all distinct consent purposes",
                            "Create separate checkbox for each purpose",
                            "Allow users to consent to each independently",
                            "Do not force all consents to proceed",
                            "Mark which consents are required vs optional"
                        ]
                    }
                ))

        return findings

    def _detect_hidden_consent(self, soup: BeautifulSoup, page: CrawledPage) -> List[Finding]:
        """Detect hidden or difficult-to-find consent elements."""
        findings = []

        # Find consent checkboxes that may be hidden
        checkboxes = soup.find_all("input", {"type": "checkbox"})

        for cb in checkboxes:
            style = cb.get("style", "")
            class_attr = cb.get("class", [])
            class_str = " ".join(class_attr) if isinstance(class_attr, list) else str(class_attr)

            # Check for hidden styles
            hidden_indicators = [
                "display:none", "display: none",
                "visibility:hidden", "visibility: hidden",
                "opacity:0", "opacity: 0",
                "hidden",
            ]

            is_hidden = any(ind in style.lower() or ind in class_str.lower()
                           for ind in hidden_indicators)

            if is_hidden:
                label_text = ""
                label_id = cb.get("id")
                if label_id:
                    label = soup.find("label", {"for": label_id})
                    if label:
                        label_text = label.get_text().lower()

                if any(kw in label_text for kw in self.CONSENT_KEYWORDS):
                    findings.append(Finding(
                        check_type=CheckType.DARK_PATTERN_HIDDEN_OPTION,
                        severity=FindingSeverity.CRITICAL,
                        status=FindingStatus.FAIL,
                        title="Hidden consent checkbox detected",
                        description="A consent checkbox appears to be hidden from users. This prevents informed consent.",
                        location=page.url,
                        element_selector=f"input[id='{label_id}']" if label_id else None,
                        dpdp_section=self.dpdp_section,
                        remediation="Ensure all consent checkboxes are clearly visible to users.",
                    ))

        return findings

    def _detect_withdrawal_issues(self, soup: BeautifulSoup, page: CrawledPage) -> List[Finding]:
        """Check for consent withdrawal mechanism."""
        findings = []
        text_content = soup.get_text().lower()

        # Keywords for withdrawal mechanism
        withdrawal_keywords = [
            "withdraw consent", "revoke consent", "opt out", "opt-out",
            "unsubscribe", "manage preferences", "privacy settings",
            "सहमति वापस", "ऑप्ट आउट", "अनसब्सक्राइब",
        ]

        has_withdrawal = any(kw in text_content for kw in withdrawal_keywords)

        # Check if this appears to be a form page with consent
        has_consent_form = any(
            kw in text_content for kw in self.CONSENT_KEYWORDS
        ) and soup.find("form")

        if has_consent_form and not has_withdrawal:
            visual_content = [
                "CONSENT WITHDRAWAL MECHANISM MISSING",
                "",
                "DPDP Section 6(6) Requirement:",
                "  Withdrawal must be as easy as giving consent",
                "",
                "Current State:",
                "  ✓ Consent collection form present",
                "  ✗ No withdrawal mechanism found",
                "  ✗ No 'opt-out' or 'unsubscribe' option",
                "",
                "PENALTY RISK: ₹50 crore",
            ]
            visual_box = generate_visual_box("WITHDRAWAL MISSING", visual_content)

            findings.append(Finding(
                check_type=CheckType.WITHDRAWAL_VISIBLE,
                severity=FindingSeverity.HIGH,
                status=FindingStatus.FAIL,
                title="No consent withdrawal mechanism found",
                description="Page collects consent but does not mention how users can withdraw consent. DPDP requires easy consent withdrawal.",
                location=page.url,
                dpdp_section=self.dpdp_section,
                remediation="Add clear information about how users can withdraw their consent at any time.",
                extra_data={
                    "violation_type": "missing_withdrawal_mechanism",
                    "keywords_searched": withdrawal_keywords[:5],
                    "penalty_risk": "₹50 crore",
                    "visual_representation": visual_box,
                    "code_fix_example": '''
<!-- Add consent withdrawal section -->
<section id="manage-consent">
  <h3>Manage Your Consent</h3>
  <p>You can withdraw your consent at any time:</p>

  <div class="consent-options">
    <a href="/settings/privacy" class="btn">Privacy Settings</a>
    <a href="/unsubscribe" class="btn">Unsubscribe from Emails</a>
    <button onclick="withdrawAllConsent()">Withdraw All Consent</button>
  </div>

  <p>Email: privacy@company.com to request consent withdrawal</p>
</section>

<!-- Hindi version -->
<section lang="hi">
  <h3>अपनी सहमति प्रबंधित करें</h3>
  <p>आप किसी भी समय अपनी सहमति वापस ले सकते हैं</p>
</section>''',
                    "dpdp_reference": {
                        "section": "Section 6(6)",
                        "requirement": "Withdrawal of consent must be as easy as giving consent",
                        "penalty": "Up to ₹50 crore"
                    },
                    "fix_steps": [
                        "Add 'Withdraw Consent' or 'Opt Out' link",
                        "Provide privacy settings page",
                        "Add unsubscribe option for marketing",
                        "Ensure withdrawal is as easy as giving consent",
                        "Include Hindi: सहमति वापस लें"
                    ]
                }
            ))

        return findings

    def _detect_cookie_consent_issues(self, page: CrawledPage) -> List[Finding]:
        """Detect cookie consent banner issues."""
        findings = []

        # Check cookie consent elements
        for element in page.consent_elements:
            if element.get("type") == "banner":
                banner_text = element.get("text", "").lower()

                # Check for accept-only option (no reject)
                has_accept = "accept" in banner_text or "agree" in banner_text
                has_reject = "reject" in banner_text or "decline" in banner_text or "refuse" in banner_text

                if has_accept and not has_reject:
                    visual_content = [
                        "COOKIE BANNER - NO REJECT OPTION",
                        "",
                        "Dark Pattern: Forced Action",
                        "",
                        "Current State:",
                        "  ✓ 'Accept' button present",
                        "  ✗ No 'Reject' or 'Decline' option",
                        "",
                        "DPDP Requirement:",
                        "  Equal prominence for accept/reject",
                        "",
                        "PENALTY RISK: ₹50 crore",
                    ]
                    visual_box = generate_visual_box("COOKIE REJECT MISSING", visual_content)

                    findings.append(Finding(
                        check_type=CheckType.DARK_PATTERN_FORCED_ACTION,
                        severity=FindingSeverity.HIGH,
                        status=FindingStatus.FAIL,
                        title="Cookie banner lacks reject option",
                        description="Cookie consent banner provides accept option but no clear reject/decline option.",
                        location=page.url,
                        dpdp_section=self.dpdp_section,
                        remediation="Provide equally prominent accept and reject options in cookie consent banners.",
                        extra_data={
                            "violation_type": "cookie_forced_accept",
                            "banner_text": banner_text[:200],
                            "penalty_risk": "₹50 crore",
                            "visual_representation": visual_box,
                            "code_before": '''
<!-- Non-compliant cookie banner (BAD) -->
<div class="cookie-banner">
  <p>We use cookies to improve your experience.</p>
  <button class="btn-primary">Accept All</button>
</div>''',
                            "code_after": '''
<!-- Compliant cookie banner (GOOD) -->
<div class="cookie-banner">
  <p>We use cookies to improve your experience.</p>
  <div class="button-group">
    <button class="btn-primary" onclick="acceptCookies()">Accept All</button>
    <button class="btn-secondary" onclick="rejectCookies()">Reject All</button>
    <button class="btn-outline" onclick="manageCookies()">Manage Preferences</button>
  </div>
</div>''',
                            "dpdp_reference": {
                                "section": "Section 6",
                                "requirement": "Consent must be free - cannot be forced",
                                "penalty": "Up to ₹50 crore"
                            },
                            "fix_steps": [
                                "Add 'Reject All' or 'Decline' button",
                                "Make reject option equally visible as accept",
                                "Add 'Manage Preferences' for granular control",
                                "Don't pre-load tracking until consent given"
                            ]
                        }
                    ))

            elif element.get("type") == "checkbox":
                if element.get("preChecked"):
                    checkbox_label = element.get('label', '')[:100]
                    visual_content = [
                        "COOKIE CHECKBOX PRE-CHECKED",
                        "",
                        "Dark Pattern: Pre-selected Consent",
                        "",
                        f"Checkbox: {checkbox_label[:40]}...",
                        "",
                        "  ┌─────────────────────────────┐",
                        "  │  ☑ [Cookie consent text]   │  ← VIOLATION",
                        "  └─────────────────────────────┘",
                        "",
                        "DPDP Section 6 - Must be unchecked",
                        "PENALTY RISK: ₹50 crore",
                    ]
                    visual_box = generate_visual_box("PRE-CHECKED COOKIE", visual_content)

                    findings.append(Finding(
                        check_type=CheckType.DARK_PATTERN_PRESELECTED,
                        severity=FindingSeverity.CRITICAL,
                        status=FindingStatus.FAIL,
                        title="Cookie consent checkbox pre-checked",
                        description=f"Cookie consent checkbox '{checkbox_label}' is pre-checked.",
                        location=page.url,
                        dpdp_section=self.dpdp_section,
                        remediation="Remove pre-checked state from cookie consent checkboxes.",
                        extra_data={
                            "violation_type": "cookie_prechecked",
                            "checkbox_label": checkbox_label,
                            "penalty_risk": "₹50 crore",
                            "visual_representation": visual_box,
                            "code_before": f'<input type="checkbox" id="cookie-consent" checked>',
                            "code_after": '<input type="checkbox" id="cookie-consent">',
                            "dpdp_reference": {
                                "section": "Section 6(1)",
                                "requirement": "Consent must be clear affirmative action - not pre-selected",
                                "penalty": "Up to ₹50 crore"
                            },
                            "fix_steps": [
                                "Remove 'checked' attribute from checkbox",
                                "Require explicit click to enable cookies",
                                "Don't load tracking cookies until consent given"
                            ]
                        }
                    ))

        return findings
