"""
DPDP GUI Compliance Scanner - Dark Pattern Detector

Detects manipulative UI patterns that violate DPDP compliance.
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
    # Clean up whitespace
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
        # Truncate if too long
        display_line = line[:width-6] if len(line) > width-6 else line
        lines.append(f"│  {display_line:<{width-6}}  │")
    lines.append(f"└{border}┘")
    return "\n".join(lines)


class DarkPatternDetector(BaseDetector):
    """
    Detector for Dark Patterns in user interfaces.

    Checks for:
    - Misdirection (confusing design)
    - Trick questions
    - Hidden costs
    - Privacy Zuckering (confusing privacy settings)
    - Forced continuity
    - Confirmshaming
    - Disguised ads
    - Nagging
    - Roach motel (hard to cancel)
    """

    dpdp_section = "Dark Patterns"
    description = "Detects manipulative UI patterns"

    async def detect(self, page: CrawledPage) -> List[Finding]:
        """Detect dark patterns on the page."""
        findings = []

        soup = BeautifulSoup(page.html_content, "html.parser")

        # Detect various dark patterns
        findings.extend(self._detect_confirmshaming(soup, page))
        findings.extend(self._detect_misdirection(soup, page))
        findings.extend(self._detect_nagging(soup, page))
        findings.extend(self._detect_roach_motel(soup, page))
        findings.extend(self._detect_bait_and_switch(soup, page))
        findings.extend(self._detect_hidden_info(soup, page))
        findings.extend(self._detect_false_urgency(soup, page))

        return findings

    def _detect_confirmshaming(self, soup: BeautifulSoup, page: CrawledPage) -> List[Finding]:
        """
        Detect confirmshaming - making users feel bad for declining.

        Examples:
        - "No thanks, I don't want to save money"
        - "I'll pass on this great offer"
        """
        findings = []

        # Patterns for confirmshaming
        shame_patterns = [
            r"no\s*,?\s*i\s*(don'?t|do\s*not)\s*want",
            r"no\s*thanks\s*,?\s*i",
            r"i'?ll\s*pass",
            r"i\s*prefer\s*not\s*to",
            r"no\s*,?\s*i'?m\s*not\s*interested",
            r"i\s*don'?t\s*care\s*about",
            r"skip\s*and\s*miss",
            # Hindi patterns
            r"नहीं\s*,?\s*मुझे\s*नहीं\s*चाहिए",
            r"मैं\s*छोड़ना\s*चाहता",
        ]

        # Find buttons and links with shaming language
        clickable = soup.find_all(["button", "a", "span", "div"], class_=lambda x: x and any(c in str(x).lower() for c in ["btn", "button", "link", "cta"]))
        clickable.extend(soup.find_all("button"))
        clickable.extend(soup.find_all("a"))

        for element in clickable:
            text = element.get_text().strip()
            text_lower = text.lower()

            for pattern in shame_patterns:
                if re.search(pattern, text_lower, re.IGNORECASE):
                    # Generate detailed extra_data
                    element_html = get_element_html(element)

                    # Generate fixed code
                    code_before = element_html
                    code_after = re.sub(
                        r'>.*<',
                        '>No, thanks<',
                        element_html
                    ) if '<' in element_html else f'<button class="btn">No, thanks</button>'

                    # Visual representation
                    visual_content = [
                        f"Pattern Type: CONFIRM SHAMING",
                        f"",
                        f"Current Button Text:",
                        f"  '{text[:50]}...' " if len(text) > 50 else f"  '{text}'",
                        f"       ↑",
                        f"  VIOLATION: Guilt-inducing language",
                        f"",
                        f"Neutral Alternative:",
                        f"  'No, thanks' or 'Decline'",
                    ]
                    visual_box = generate_visual_box("DARK PATTERN DETECTED", visual_content)

                    findings.append(Finding(
                        check_type=CheckType.DARK_PATTERN_CONFIRM_SHAMING,
                        severity=FindingSeverity.MEDIUM,
                        status=FindingStatus.FAIL,
                        title="Confirmshaming detected",
                        description=f"Button/link uses guilt-inducing language: '{text[:100]}'. This manipulates users into making choices they might not want.",
                        location=page.url,
                        element_selector=code_before,
                        dpdp_section=self.dpdp_section,
                        remediation="Use neutral language for decline options, e.g., 'No, thanks' or 'Decline'.",
                        extra_data={
                            "pattern_type": "confirm_shaming",
                            "element_text": text,
                            "code_before": code_before,
                            "code_after": code_after,
                            "penalty_risk": "Consumer Protection Act violation",
                            "visual_representation": visual_box,
                            "fix_steps": [
                                "Replace guilt-inducing text with neutral language",
                                "Use equal visual weight for both Yes and No options",
                                "Remove emotional manipulation"
                            ]
                        }
                    ))
                    break

        return findings

    def _detect_misdirection(self, soup: BeautifulSoup, page: CrawledPage) -> List[Finding]:
        """
        Detect misdirection - using visual design to draw attention away from important info.
        """
        findings = []

        # Check for tiny text near forms or consent
        small_text_elements = soup.find_all(style=re.compile(r'font-size:\s*(0?\.[0-9]+|[0-9]|1[0-1])px', re.I))

        forms = soup.find_all("form")
        for form in forms:
            # Look for very small text within forms
            small_in_form = form.find_all(style=re.compile(r'font-size:\s*([0-9]|1[0-1])px', re.I))

            for small in small_in_form:
                text = small.get_text().lower()

                # Check if important terms are hidden in small text
                important_keywords = [
                    "consent", "agree", "privacy", "terms", "data",
                    "share", "third party", "subscribe", "charge",
                ]

                if any(kw in text for kw in important_keywords):
                    element_html = get_element_html(small)

                    # Extract font size from style
                    style = small.get('style', '')
                    font_match = re.search(r'font-size:\s*(\d+)px', style, re.I)
                    current_font_size = font_match.group(1) if font_match else "small"

                    # Generate fixed code
                    code_before = element_html
                    code_after = re.sub(
                        r'font-size:\s*\d+px',
                        'font-size: 14px',
                        element_html
                    )

                    # Visual representation
                    visual_content = [
                        f"Pattern Type: MISDIRECTION",
                        f"",
                        f"Current Font Size: {current_font_size}px",
                        f"Required Minimum: 12px",
                        f"",
                        f"Important keywords detected:",
                        f"  • {[kw for kw in important_keywords if kw in text][:3]}",
                        f"",
                        f"Text Preview:",
                        f"  '{text[:40]}...'",
                    ]
                    visual_box = generate_visual_box("MISDIRECTION DETECTED", visual_content)

                    findings.append(Finding(
                        check_type=CheckType.DARK_PATTERN_MISDIRECTION,
                        severity=FindingSeverity.MEDIUM,
                        status=FindingStatus.FAIL,
                        title="Important information in very small text",
                        description=f"Important consent/privacy-related text is displayed in very small font ({current_font_size}px): '{text[:100]}'",
                        location=page.url,
                        element_selector=code_before,
                        dpdp_section=self.dpdp_section,
                        remediation="Display important privacy and consent information in readable font sizes (at least 12px).",
                        extra_data={
                            "pattern_type": "misdirection",
                            "element_text": text[:200],
                            "current_font_size": f"{current_font_size}px",
                            "required_font_size": "12px minimum",
                            "code_before": code_before,
                            "code_after": code_after,
                            "penalty_risk": "DPDP Section 6 - Invalid consent due to lack of clarity",
                            "visual_representation": visual_box,
                            "keywords_found": [kw for kw in important_keywords if kw in text],
                            "fix_steps": [
                                f"Increase font-size from {current_font_size}px to at least 12px",
                                "Ensure important text has equal visual prominence",
                                "Consider using bold or contrasting colors for emphasis"
                            ]
                        }
                    ))

        return findings

    def _detect_nagging(self, soup: BeautifulSoup, page: CrawledPage) -> List[Finding]:
        """
        Detect nagging - repeatedly asking for something.

        Look for multiple modal/popup triggers or persistent banners.
        """
        findings = []

        # Count number of modal/popup elements
        modal_classes = ["modal", "popup", "overlay", "lightbox", "dialog"]
        modals = []

        for class_name in modal_classes:
            modals.extend(soup.find_all(class_=re.compile(class_name, re.I)))

        # If multiple consent/subscription modals
        consent_modals = [m for m in modals
                        if any(kw in m.get_text().lower()
                              for kw in ["subscribe", "newsletter", "consent", "notification"])]

        if len(consent_modals) > 1:
            findings.append(Finding(
                check_type=CheckType.DARK_PATTERN_URGENCY,
                severity=FindingSeverity.LOW,
                status=FindingStatus.FAIL,
                title="Multiple consent/subscription popups detected",
                description=f"Page contains {len(consent_modals)} modal elements asking for consent or subscriptions. This may indicate nagging behavior.",
                location=page.url,
                dpdp_section=self.dpdp_section,
                remediation="Limit consent requests to once per session. Respect user's choice.",
            ))

        return findings

    def _detect_roach_motel(self, soup: BeautifulSoup, page: CrawledPage) -> List[Finding]:
        """
        Detect roach motel - easy to get in, hard to get out.

        Check if unsubscribe/delete account is hidden or complex.
        """
        findings = []
        text_content = soup.get_text().lower()

        # Check for account-related pages
        account_keywords = ["account", "profile", "settings", "preferences"]
        is_account_page = any(kw in page.url.lower() or kw in text_content[:500]
                            for kw in account_keywords)

        if is_account_page:
            # Look for delete/unsubscribe options
            exit_keywords = [
                "delete account", "close account", "deactivate",
                "unsubscribe", "cancel subscription", "opt out",
                "remove my data", "erase my data",
                "खाता हटाएं", "अनसब्सक्राइब",
            ]

            has_exit = any(kw in text_content for kw in exit_keywords)

            if not has_exit:
                # Visual representation for Roach Motel
                visual_content = [
                    f"Pattern Type: ROACH MOTEL",
                    f"",
                    f"Page: Account/Settings Page",
                    f"",
                    f"Expected Options (MISSING):",
                    f"  ✗ Delete Account",
                    f"  ✗ Unsubscribe",
                    f"  ✗ Cancel Subscription",
                    f"  ✗ Remove My Data",
                    f"",
                    f"VIOLATION: Easy sign-up, hard exit",
                    f"",
                    f"DPDP Section 6(6) - Withdrawal Requirement",
                ]
                visual_box = generate_visual_box("ROACH MOTEL DETECTED", visual_content)

                # Sample code to add
                code_fix_example = '''
<div class="danger-zone card">
  <h3>Danger Zone</h3>
  <button class="btn btn-danger" onclick="deleteAccount()">
    Delete My Account
  </button>
  <button class="btn btn-outline" onclick="unsubscribe()">
    Unsubscribe from All
  </button>
  <a href="/data-deletion" class="link">
    Request Data Deletion
  </a>
</div>'''

                findings.append(Finding(
                    check_type=CheckType.DARK_PATTERN_HIDDEN_OPTION,
                    severity=FindingSeverity.HIGH,
                    status=FindingStatus.FAIL,
                    title="No account deletion/cancellation option found (Roach Motel)",
                    description="Account settings page does not show clear options to delete account, unsubscribe, or cancel services. Users can easily sign up but cannot easily leave.",
                    location=page.url,
                    dpdp_section=self.dpdp_section,
                    remediation="Provide clear and accessible options to delete account, unsubscribe, and cancel services. DPDP Section 6(6) requires easy withdrawal.",
                    extra_data={
                        "pattern_type": "roach_motel",
                        "missing_options": [
                            "Delete Account",
                            "Unsubscribe",
                            "Cancel Subscription",
                            "Remove My Data",
                            "Opt Out"
                        ],
                        "code_fix_example": code_fix_example,
                        "penalty_risk": "₹50 crore - DPDP Section 6(6) violation",
                        "visual_representation": visual_box,
                        "fix_steps": [
                            "Add 'Delete Account' button prominently on settings page",
                            "Add 'Unsubscribe' option for each subscription",
                            "Provide 'Cancel Subscription' link for paid services",
                            "Create dedicated 'Data Deletion Request' page",
                            "Ensure exit options are as easy as sign-up"
                        ],
                        "dpdp_reference": {
                            "section": "Section 6(6)",
                            "requirement": "Withdrawal of consent must be as easy as giving consent",
                            "penalty": "Up to ₹50 crore"
                        }
                    }
                ))

        return findings

    def _detect_bait_and_switch(self, soup: BeautifulSoup, page: CrawledPage) -> List[Finding]:
        """
        Detect bait and switch - making users think they're doing one thing but doing another.
        """
        findings = []

        # Look for misleading button labels
        buttons = soup.find_all(["button", "input", "a"])

        for btn in buttons:
            btn_text = btn.get_text().lower().strip() if btn.name != "input" else btn.get("value", "").lower()
            onclick = btn.get("onclick", "").lower()
            href = btn.get("href", "").lower()

            # Check for misleading close buttons that actually consent
            if btn_text in ["x", "close", "dismiss", "got it", "ok"]:
                # Check if action implies consent
                action_text = onclick + href
                if any(kw in action_text for kw in ["consent", "accept", "agree", "subscribe"]):
                    findings.append(Finding(
                        check_type=CheckType.DARK_PATTERN_FORCED_ACTION,
                        severity=FindingSeverity.HIGH,
                        status=FindingStatus.FAIL,
                        title="Misleading close/dismiss button",
                        description=f"Button labeled '{btn_text}' appears to dismiss but actually triggers consent/subscription action.",
                        location=page.url,
                        element_selector=str(btn)[:500],
                        dpdp_section=self.dpdp_section,
                        remediation="Ensure button labels accurately describe their action. Close buttons should only close, not consent.",
                    ))

        return findings

    def _detect_hidden_info(self, soup: BeautifulSoup, page: CrawledPage) -> List[Finding]:
        """
        Detect important information hidden in expandable sections or fine print.
        """
        findings = []

        # Look for collapsible sections with privacy content
        accordions = soup.find_all(class_=re.compile(r'(accordion|collapse|expand|toggle)', re.I))
        details = soup.find_all("details")

        hidden_containers = accordions + details

        for container in hidden_containers:
            text = container.get_text().lower()

            # Check if important info is hidden
            important_terms = [
                "data sharing", "third party", "sell your data", "share your information",
                "tracking", "profiling", "automated decision",
            ]

            if any(term in text for term in important_terms):
                findings.append(Finding(
                    check_type=CheckType.DARK_PATTERN_HIDDEN_OPTION,
                    severity=FindingSeverity.MEDIUM,
                    status=FindingStatus.FAIL,
                    title="Important privacy information in collapsed/hidden section",
                    description="Key data processing information is hidden in an expandable section, making it less visible to users.",
                    location=page.url,
                    element_selector=str(container)[:500],
                    dpdp_section=self.dpdp_section,
                    remediation="Display important privacy and data sharing information prominently, not in collapsed sections.",
                ))

        return findings

    def _detect_false_urgency(self, soup: BeautifulSoup, page: CrawledPage) -> List[Finding]:
        """
        Detect false urgency - creating artificial time pressure.
        """
        findings = []
        text_content = soup.get_text().lower()

        # Urgency patterns
        urgency_patterns = [
            r"only\s*\d+\s*(left|remaining)",
            r"hurry\s*,?\s*(offer|sale|deal)",
            r"limited\s*time\s*(offer|only)",
            r"act\s*now",
            r"don'?t\s*miss\s*(out|this)",
            r"expires?\s*(soon|today|in\s*\d+)",
            r"last\s*chance",
            r"ends?\s*(today|tonight|soon)",
            r"\d+\s*people\s*(viewing|watching)",
        ]

        for pattern in urgency_patterns:
            matches = re.findall(pattern, text_content)
            if matches:
                # Check if this is in context of consent/data collection
                consent_context = any(kw in text_content for kw in ["consent", "agree", "data", "privacy", "subscribe"])

                if consent_context:
                    # Find the urgency text element
                    urgency_elements = soup.find_all(string=re.compile(pattern, re.I))
                    urgency_text = matches[0] if matches else pattern

                    # Visual representation
                    visual_content = [
                        f"Pattern Type: FALSE URGENCY",
                        f"",
                        f"Detected Language:",
                        f"  '{urgency_text}'",
                        f"",
                        f"Context: Near consent/data collection",
                        f"",
                        f"VIOLATION:",
                        f"  Creating artificial time pressure",
                        f"  to manipulate consent decisions",
                        f"",
                        f"Consumer Protection Act - Dark Patterns",
                    ]
                    visual_box = generate_visual_box("FALSE URGENCY DETECTED", visual_content)

                    findings.append(Finding(
                        check_type=CheckType.DARK_PATTERN_URGENCY,
                        severity=FindingSeverity.MEDIUM,
                        status=FindingStatus.FAIL,
                        title="False urgency near consent/data collection",
                        description=f"Urgency-creating language found near consent or data collection elements. Detected: '{urgency_text}'",
                        location=page.url,
                        dpdp_section=self.dpdp_section,
                        remediation="Avoid creating artificial urgency when requesting consent or collecting personal data. Remove countdown timers and scarcity language from consent flows.",
                        extra_data={
                            "pattern_type": "false_urgency",
                            "detected_pattern": pattern,
                            "urgency_text": urgency_text,
                            "penalty_risk": "Consumer Protection Act - Dark Patterns violation",
                            "visual_representation": visual_box,
                            "examples_found": matches[:5],
                            "fix_steps": [
                                "Remove countdown timers from consent/subscription pages",
                                "Remove 'Only X left' scarcity messages",
                                "Remove 'Hurry' and 'Act now' language",
                                "Allow users time to make informed decisions",
                                "Consent should be freely given, not under pressure"
                            ]
                        }
                    ))
                    break  # Only report once per page

        return findings
