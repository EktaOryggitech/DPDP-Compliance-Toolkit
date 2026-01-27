"""
DPDP GUI Compliance Scanner - Privacy Notice Detector

Detects privacy notice compliance issues per DPDP Section 5.
"""
import re
from typing import List, Optional
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


class PrivacyNoticeDetector(BaseDetector):
    """
    Detector for DPDP Section 5 - Notice Requirements.

    Checks for:
    - Presence of privacy notice/policy
    - Required content in privacy notice
    - Readability and language accessibility
    - Prominent placement and accessibility
    """

    dpdp_section = "Section 5"
    description = "Detects privacy notice compliance issues"

    # Keywords indicating privacy notice pages
    PRIVACY_KEYWORDS = [
        "privacy policy", "privacy notice", "data protection",
        "गोपनीयता नीति", "गोपनीयता सूचना", "डेटा संरक्षण",
        "personal data", "personal information",
        "व्यक्तिगत डेटा", "व्यक्तिगत जानकारी",
    ]

    # Required elements in privacy notice (DPDP Section 5)
    REQUIRED_ELEMENTS = {
        "data_collected": [
            "personal data", "information we collect", "data we collect",
            "types of data", "categories of data",
            "एकत्रित डेटा", "हम एकत्र करते हैं",
        ],
        "purpose": [
            "purpose", "why we collect", "how we use", "use of data",
            "उद्देश्य", "हम क्यों एकत्र करते हैं", "उपयोग",
        ],
        "data_fiduciary": [
            "data fiduciary", "controller", "company", "organization",
            "who we are", "about us", "contact",
            "डेटा न्यासी", "कंपनी", "संगठन", "संपर्क",
        ],
        "rights": [
            "your rights", "data subject rights", "rights of the principal",
            "access", "correction", "erasure", "withdraw consent",
            "आपके अधिकार", "पहुंच", "सुधार", "विलोपन", "सहमति वापस",
        ],
        "grievance": [
            "grievance", "complaint", "contact us", "dpo", "data protection officer",
            "शिकायत", "संपर्क करें", "डेटा संरक्षण अधिकारी",
        ],
    }

    async def detect(self, page: CrawledPage) -> List[Finding]:
        """Detect privacy notice issues on the page."""
        findings = []

        # Check if this is a privacy-related page
        is_privacy_page = self._is_privacy_page(page)

        # Check for privacy notice link on non-privacy pages
        if not is_privacy_page:
            has_link = self._check_privacy_link(page)
            if not has_link:
                visual_content = [
                    "VIOLATION: Missing Privacy Notice Link",
                    "",
                    "Page scanned: " + page.url[:45] + "...",
                    "",
                    "Expected Elements (NOT FOUND):",
                    "  ✗ Footer link to Privacy Policy",
                    "  ✗ Navigation menu Privacy link",
                    "  ✗ Any 'Privacy' or 'Data Protection' link",
                    "",
                    "DPDP Section 5 - Notice Requirement",
                ]
                visual_box = generate_visual_box("PRIVACY NOTICE LINK MISSING", visual_content)

                findings.append(Finding(
                    check_type=CheckType.PRIVACY_NOTICE_MISSING_LINK,
                    severity=FindingSeverity.HIGH,
                    status=FindingStatus.FAIL,
                    title="Privacy notice link not found",
                    description="No link to privacy policy/notice found on this page. Users should be able to easily access privacy information.",
                    location=page.url,
                    dpdp_section=self.dpdp_section,
                    remediation="Add a prominent link to the privacy notice in the footer or navigation menu.",
                    extra_data={
                        "violation_type": "missing_privacy_link",
                        "page_url": page.url,
                        "code_fix_example": '''
<!-- Add to footer -->
<footer>
  <a href="/privacy-policy">Privacy Policy</a>
  <a href="/privacy-policy" lang="hi">गोपनीयता नीति</a>
</footer>

<!-- Or add to navigation -->
<nav>
  <a href="/privacy-policy">Privacy Policy</a>
</nav>''',
                        "penalty_risk": "₹50 crore - DPDP Section 5 violation",
                        "visual_representation": visual_box,
                        "dpdp_reference": {
                            "section": "Section 5",
                            "requirement": "Data Fiduciary must give notice with specified information",
                            "penalty": "Up to ₹50 crore"
                        },
                        "fix_steps": [
                            "Add a 'Privacy Policy' link in the website footer",
                            "Ensure the link is visible on all pages",
                            "Consider adding Hindi translation: गोपनीयता नीति",
                            "Link should lead to a comprehensive privacy notice"
                        ]
                    }
                ))
        else:
            # Analyze privacy notice content
            content_findings = await self._analyze_privacy_content(page)
            findings.extend(content_findings)

        return findings

    def _is_privacy_page(self, page: CrawledPage) -> bool:
        """Check if this page is a privacy notice/policy page."""
        # Check URL
        url_lower = page.url.lower()
        if any(kw.replace(" ", "-") in url_lower or kw.replace(" ", "_") in url_lower
               for kw in ["privacy policy", "privacy-policy", "privacy_policy",
                          "privacy-notice", "data-protection"]):
            return True

        # Check title
        title_lower = page.title.lower() if page.title else ""
        if any(kw in title_lower for kw in self.PRIVACY_KEYWORDS):
            return True

        # Check page content heading
        soup = BeautifulSoup(page.html_content, "html.parser")
        h1_tags = soup.find_all("h1")
        for h1 in h1_tags:
            h1_text = h1.get_text().lower()
            if any(kw in h1_text for kw in self.PRIVACY_KEYWORDS):
                return True

        return False

    def _check_privacy_link(self, page: CrawledPage) -> bool:
        """Check if page has a link to privacy notice."""
        soup = BeautifulSoup(page.html_content, "html.parser")

        # Check all links
        for link in soup.find_all("a"):
            href = link.get("href", "").lower()
            text = link.get_text().lower()

            privacy_patterns = [
                "privacy", "data-protection", "data_protection",
                "गोपनीयता", "निजता",
            ]

            if any(p in href or p in text for p in privacy_patterns):
                return True

        return False

    async def _analyze_privacy_content(self, page: CrawledPage) -> List[Finding]:
        """Analyze privacy notice content for required elements."""
        findings = []
        soup = BeautifulSoup(page.html_content, "html.parser")
        text_content = soup.get_text().lower()

        # Check for each required element
        for element_name, keywords in self.REQUIRED_ELEMENTS.items():
            found = any(kw in text_content for kw in keywords)

            if not found:
                check_type_map = {
                    "data_collected": CheckType.PRIVACY_NOTICE_MISSING_DATA_TYPES,
                    "purpose": CheckType.PRIVACY_NOTICE_MISSING_PURPOSE,
                    "data_fiduciary": CheckType.PRIVACY_NOTICE_MISSING_FIDUCIARY,
                    "rights": CheckType.PRIVACY_NOTICE_MISSING_RIGHTS,
                    "grievance": CheckType.PRIVACY_NOTICE_MISSING_GRIEVANCE,
                }

                title_map = {
                    "data_collected": "Missing description of personal data collected",
                    "purpose": "Missing purpose of data collection",
                    "data_fiduciary": "Missing Data Fiduciary identification",
                    "rights": "Missing Data Principal rights information",
                    "grievance": "Missing grievance redressal mechanism",
                }

                code_examples = {
                    "data_collected": '''
<section id="data-collected">
  <h2>Personal Data We Collect</h2>
  <ul>
    <li>Name, email, phone number</li>
    <li>Address and location data</li>
    <li>Payment information</li>
    <li>Usage data and preferences</li>
  </ul>
</section>''',
                    "purpose": '''
<section id="purpose">
  <h2>Purpose of Data Collection</h2>
  <ul>
    <li>To provide and maintain our services</li>
    <li>To process transactions</li>
    <li>To send service-related communications</li>
    <li>To improve user experience</li>
  </ul>
</section>''',
                    "data_fiduciary": '''
<section id="data-fiduciary">
  <h2>About Us (Data Fiduciary)</h2>
  <p>Company Name: [Your Company]</p>
  <p>Registered Address: [Address]</p>
  <p>Contact: [Email/Phone]</p>
  <p>CIN: [Company Registration Number]</p>
</section>''',
                    "rights": '''
<section id="your-rights">
  <h2>Your Rights as Data Principal</h2>
  <ul>
    <li>Right to access your personal data</li>
    <li>Right to correction of inaccurate data</li>
    <li>Right to erasure of your data</li>
    <li>Right to withdraw consent</li>
    <li>Right to nominate</li>
  </ul>
</section>''',
                    "grievance": '''
<section id="grievance">
  <h2>Grievance Redressal</h2>
  <p>Grievance Officer: [Name]</p>
  <p>Email: grievance@company.com</p>
  <p>Phone: [Number]</p>
  <p>Address: [Office Address]</p>
  <p>Response time: Within 30 days</p>
</section>'''
                }

                visual_content = [
                    f"VIOLATION: Missing {element_name.replace('_', ' ').title()}",
                    "",
                    f"Privacy Notice Page: {page.url[:40]}...",
                    "",
                    "Required Content (NOT FOUND):",
                    f"  ✗ {element_name.replace('_', ' ').title()} section",
                    "",
                    f"Keywords searched: {', '.join(keywords[:3])}...",
                    "",
                    "DPDP Section 5(2) - Required Notice Content",
                ]
                visual_box = generate_visual_box(f"MISSING: {element_name.upper()}", visual_content)

                findings.append(Finding(
                    check_type=check_type_map.get(element_name, CheckType.PRIVACY_NOTICE_INCOMPLETE),
                    severity=FindingSeverity.HIGH if element_name in ["data_collected", "purpose", "grievance"] else FindingSeverity.MEDIUM,
                    status=FindingStatus.FAIL,
                    title=title_map.get(element_name, f"Missing {element_name}"),
                    description=f"Privacy notice does not contain required information about {element_name.replace('_', ' ')}. This is required under DPDP Section 5.",
                    location=page.url,
                    dpdp_section=self.dpdp_section,
                    remediation=f"Add clear information about {element_name.replace('_', ' ')} to the privacy notice.",
                    extra_data={
                        "violation_type": f"missing_{element_name}",
                        "missing_element": element_name,
                        "keywords_searched": keywords,
                        "code_fix_example": code_examples.get(element_name, ""),
                        "penalty_risk": "₹50 crore - DPDP Section 5 violation" if element_name in ["data_collected", "purpose", "grievance"] else "₹10 crore - DPDP Section 5 violation",
                        "visual_representation": visual_box,
                        "dpdp_reference": {
                            "section": "Section 5(2)",
                            "requirement": f"Privacy notice must include {element_name.replace('_', ' ')}",
                            "penalty": "Up to ₹50 crore"
                        },
                        "fix_steps": [
                            f"Add a dedicated section for {element_name.replace('_', ' ')}",
                            "Use clear, simple language",
                            "Provide Hindi translation for Indian users",
                            "Ensure the information is easily findable"
                        ]
                    }
                ))

        # Check for language accessibility (Hindi)
        hindi_pattern = re.compile(r'[\u0900-\u097F]')
        has_hindi = bool(hindi_pattern.search(text_content))

        if not has_hindi:
            visual_content = [
                "VIOLATION: Missing Hindi Translation",
                "",
                "Privacy notice is only in English",
                "",
                "DPDP Requirement:",
                "  Notice should be in language user understands",
                "  Hindi is official language of India",
                "",
                "Recommended:",
                "  ✓ Add Hindi version: गोपनीयता नीति",
                "  ✓ Add language toggle button",
                "",
                "DPDP Section 5 - Accessibility",
            ]
            visual_box = generate_visual_box("LANGUAGE ACCESSIBILITY", visual_content)

            findings.append(Finding(
                check_type=CheckType.PRIVACY_NOTICE_LANGUAGE,
                severity=FindingSeverity.MEDIUM,
                status=FindingStatus.FAIL,
                title="Privacy notice not available in Hindi",
                description="Privacy notice appears to be only in English. DPDP recommends notices be in languages the user understands, including Hindi for Indian users.",
                location=page.url,
                dpdp_section=self.dpdp_section,
                remediation="Provide privacy notice in Hindi and other relevant Indian languages.",
                extra_data={
                    "violation_type": "missing_hindi_translation",
                    "current_language": "English only",
                    "code_fix_example": '''
<!-- Add language toggle -->
<div class="language-selector">
  <button onclick="switchLang('en')">English</button>
  <button onclick="switchLang('hi')">हिंदी</button>
</div>

<!-- Hindi version example -->
<section lang="hi">
  <h1>गोपनीयता नीति</h1>
  <h2>हम कौन सा डेटा एकत्र करते हैं</h2>
  <p>हम निम्नलिखित व्यक्तिगत डेटा एकत्र करते हैं...</p>
  <h2>आपके अधिकार</h2>
  <p>डेटा प्रिंसिपल के रूप में, आपके पास अधिकार हैं...</p>
</section>''',
                    "penalty_risk": "₹10 crore - Accessibility violation",
                    "visual_representation": visual_box,
                    "dpdp_reference": {
                        "section": "Section 5",
                        "requirement": "Notice must be in language user understands",
                        "penalty": "Up to ₹50 crore"
                    },
                    "fix_steps": [
                        "Translate privacy notice to Hindi (हिंदी)",
                        "Add language toggle/selector on the page",
                        "Consider other regional languages based on user base",
                        "Ensure translations are accurate and legally reviewed"
                    ]
                }
            ))

        return findings
