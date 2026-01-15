"""
DPDP GUI Compliance Scanner - Dark Pattern Detector

Detects manipulative UI patterns that violate DPDP compliance.
"""
import re
from typing import List, Dict, Any
from bs4 import BeautifulSoup

from app.detectors.base import BaseDetector
from app.models.finding import CheckType, Finding, FindingSeverity
from app.scanners.web.crawler import CrawledPage


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
            text = element.get_text().lower().strip()

            for pattern in shame_patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    findings.append(Finding(
                        check_type=CheckType.DARK_PATTERN_CONFIRMSHAMING,
                        severity=FindingSeverity.MEDIUM,
                        title="Confirmshaming detected",
                        description=f"Button/link uses guilt-inducing language: '{text[:100]}'. This manipulates users into making choices they might not want.",
                        page_url=page.url,
                        element_html=str(element)[:500],
                        dpdp_section=self.dpdp_section,
                        remediation="Use neutral language for decline options, e.g., 'No, thanks' or 'Decline'.",
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
                    findings.append(Finding(
                        check_type=CheckType.DARK_PATTERN_MISDIRECTION,
                        severity=FindingSeverity.MEDIUM,
                        title="Important information in very small text",
                        description=f"Important consent/privacy-related text is displayed in very small font: '{text[:100]}'",
                        page_url=page.url,
                        element_html=str(small)[:500],
                        dpdp_section=self.dpdp_section,
                        remediation="Display important privacy and consent information in readable font sizes (at least 12px).",
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
                check_type=CheckType.DARK_PATTERN_NAGGING,
                severity=FindingSeverity.LOW,
                title="Multiple consent/subscription popups detected",
                description=f"Page contains {len(consent_modals)} modal elements asking for consent or subscriptions. This may indicate nagging behavior.",
                page_url=page.url,
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
                findings.append(Finding(
                    check_type=CheckType.DARK_PATTERN_ROACH_MOTEL,
                    severity=FindingSeverity.HIGH,
                    title="No account deletion/cancellation option found",
                    description="Account settings page does not show clear options to delete account, unsubscribe, or cancel services.",
                    page_url=page.url,
                    dpdp_section=self.dpdp_section,
                    remediation="Provide clear and accessible options to delete account, unsubscribe, and cancel services.",
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
                        check_type=CheckType.DARK_PATTERN_BAIT_SWITCH,
                        severity=FindingSeverity.HIGH,
                        title="Misleading close/dismiss button",
                        description=f"Button labeled '{btn_text}' appears to dismiss but actually triggers consent/subscription action.",
                        page_url=page.url,
                        element_html=str(btn)[:500],
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
                    check_type=CheckType.DARK_PATTERN_HIDDEN_INFO,
                    severity=FindingSeverity.MEDIUM,
                    title="Important privacy information in collapsed/hidden section",
                    description="Key data processing information is hidden in an expandable section, making it less visible to users.",
                    page_url=page.url,
                    element_html=str(container)[:500],
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
                    findings.append(Finding(
                        check_type=CheckType.DARK_PATTERN_FALSE_URGENCY,
                        severity=FindingSeverity.MEDIUM,
                        title="False urgency near consent/data collection",
                        description=f"Urgency-creating language found near consent or data collection elements. Pattern: '{pattern}'",
                        page_url=page.url,
                        dpdp_section=self.dpdp_section,
                        remediation="Avoid creating artificial urgency when requesting consent or collecting personal data.",
                    ))
                    break  # Only report once per page

        return findings
