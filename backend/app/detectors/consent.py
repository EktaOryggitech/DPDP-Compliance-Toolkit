"""
DPDP GUI Compliance Scanner - Consent Mechanism Detector

Detects consent mechanism compliance issues per DPDP Section 6.
"""
import re
from typing import List, Dict, Any
from bs4 import BeautifulSoup

from app.detectors.base import BaseDetector
from app.models.finding import CheckType, Finding, FindingSeverity
from app.scanners.web.crawler import CrawledPage


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
                    findings.append(Finding(
                        check_type=CheckType.DARK_PATTERN_PRE_CHECKED,
                        severity=FindingSeverity.CRITICAL,
                        title="Pre-checked consent checkbox detected",
                        description=f"A consent checkbox is pre-checked by default. Text: '{label_text[:100] or parent_text[:100]}'. This violates DPDP requirement for explicit, affirmative consent.",
                        page_url=page.url,
                        element_selector=f"input[id='{label_id}']" if label_id else "input[type='checkbox']",
                        element_html=str(cb)[:500],
                        dpdp_section=self.dpdp_section,
                        remediation="Remove the 'checked' attribute from consent checkboxes. Users must explicitly opt-in.",
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
                findings.append(Finding(
                    check_type=CheckType.CONSENT_BUNDLED,
                    severity=FindingSeverity.HIGH,
                    title="Bundled consent detected",
                    description=f"A single checkbox combines multiple consent purposes: {', '.join(matched_purposes[:5])}. DPDP requires granular consent for each purpose.",
                    page_url=page.url,
                    element_selector=f"input[id='{label_id}']" if label_id else None,
                    element_html=str(cb)[:500],
                    dpdp_section=self.dpdp_section,
                    remediation="Separate different consent purposes into individual checkboxes. Users should be able to consent to each purpose independently.",
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
                        check_type=CheckType.CONSENT_HIDDEN,
                        severity=FindingSeverity.CRITICAL,
                        title="Hidden consent checkbox detected",
                        description="A consent checkbox appears to be hidden from users. This prevents informed consent.",
                        page_url=page.url,
                        element_selector=f"input[id='{label_id}']" if label_id else None,
                        element_html=str(cb)[:500],
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
            findings.append(Finding(
                check_type=CheckType.CONSENT_WITHDRAWAL_MISSING,
                severity=FindingSeverity.HIGH,
                title="No consent withdrawal mechanism found",
                description="Page collects consent but does not mention how users can withdraw consent. DPDP requires easy consent withdrawal.",
                page_url=page.url,
                dpdp_section=self.dpdp_section,
                remediation="Add clear information about how users can withdraw their consent at any time.",
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
                    findings.append(Finding(
                        check_type=CheckType.DARK_PATTERN_FORCED_ACTION,
                        severity=FindingSeverity.HIGH,
                        title="Cookie banner lacks reject option",
                        description="Cookie consent banner provides accept option but no clear reject/decline option.",
                        page_url=page.url,
                        dpdp_section=self.dpdp_section,
                        remediation="Provide equally prominent accept and reject options in cookie consent banners.",
                    ))

            elif element.get("type") == "checkbox":
                if element.get("preChecked"):
                    findings.append(Finding(
                        check_type=CheckType.DARK_PATTERN_PRE_CHECKED,
                        severity=FindingSeverity.CRITICAL,
                        title="Cookie consent checkbox pre-checked",
                        description=f"Cookie consent checkbox '{element.get('label', '')[:100]}' is pre-checked.",
                        page_url=page.url,
                        dpdp_section=self.dpdp_section,
                        remediation="Remove pre-checked state from cookie consent checkboxes.",
                    ))

        return findings
