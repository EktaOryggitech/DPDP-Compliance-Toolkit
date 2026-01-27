"""
DPDP GUI Compliance Scanner - Detailed Report Formatter

Generates detailed compliance reports matching the Real-Time-Examples-Scenarios.md format.
Includes visual ASCII diagrams, code fixes, and penalty risk information.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.models.finding import Finding, FindingSeverity, FindingStatus, CheckType


def generate_box(title: str, content_lines: List[str], width: int = 60) -> str:
    """Generate ASCII box diagram."""
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


def get_severity_icon(severity: FindingSeverity) -> str:
    """Get icon for severity level."""
    icons = {
        FindingSeverity.CRITICAL: "🔴",
        FindingSeverity.HIGH: "🟠",
        FindingSeverity.MEDIUM: "🟡",
        FindingSeverity.LOW: "🟢",
        FindingSeverity.INFO: "🔵",
    }
    return icons.get(severity, "⚪")


def get_penalty_risk(severity: FindingSeverity, check_type: CheckType) -> str:
    """Get penalty risk based on severity and check type."""
    if check_type in [CheckType.CHILDREN_AGE_VERIFICATION, CheckType.CHILDREN_PARENTAL_CONSENT]:
        return "₹200 crore"
    elif severity == FindingSeverity.CRITICAL:
        return "₹250 crore"
    elif severity == FindingSeverity.HIGH:
        return "₹50 crore"
    elif severity == FindingSeverity.MEDIUM:
        return "₹10 crore"
    else:
        return "Best practice deviation"


def format_finding_detailed(finding: Finding, index: int) -> str:
    """Format a single finding in detailed Real-Time-Examples style."""
    lines = []
    extra = finding.extra_data or {}

    # Header
    lines.append(f"\n{'='*70}")
    lines.append(f"  FINDING #{index}: {finding.title}")
    lines.append(f"{'='*70}")

    # Summary table
    lines.append(f"""
| Field          | Value                                    |
|----------------|------------------------------------------|
| Check Type     | {finding.check_type.value:<40} |
| DPDP Section   | {finding.dpdp_section or 'N/A':<40} |
| Severity       | {get_severity_icon(finding.severity)} {finding.severity.value.upper():<37} |
| Status         | {finding.status.value.upper():<40} |
| Penalty Risk   | {extra.get('penalty_risk', get_penalty_risk(finding.severity, finding.check_type)):<40} |
| Location       | {(finding.location or 'N/A')[:40]:<40} |
""")

    # Visual representation (if available from extra_data)
    if extra.get('visual_representation'):
        lines.append("\n### Visual Representation")
        lines.append("```")
        lines.append(extra['visual_representation'])
        lines.append("```")

    # Description
    lines.append(f"\n### Description")
    lines.append(finding.description or "No description provided.")

    # Element/Code snippet
    if finding.element_selector:
        lines.append(f"\n### Element Detected")
        lines.append("```html")
        lines.append(finding.element_selector)
        lines.append("```")

    # Code fix (if available)
    if extra.get('code_before') and extra.get('code_after'):
        lines.append(f"\n### Code Fix")
        lines.append("**Before (VIOLATION):**")
        lines.append("```html")
        lines.append(extra['code_before'])
        lines.append("```")
        lines.append("\n**After (COMPLIANT):**")
        lines.append("```html")
        lines.append(extra['code_after'])
        lines.append("```")

    # Code fix example (if available)
    if extra.get('code_fix_example'):
        lines.append(f"\n### Code Fix Example")
        lines.append("```html")
        lines.append(extra['code_fix_example'])
        lines.append("```")

    # DPDP Reference
    if extra.get('dpdp_reference'):
        ref = extra['dpdp_reference']
        lines.append(f"\n### DPDP Reference")
        lines.append(f"- **Section:** {ref.get('section', 'N/A')}")
        lines.append(f"- **Requirement:** {ref.get('requirement', 'N/A')}")
        lines.append(f"- **Penalty:** {ref.get('penalty', 'N/A')}")

    # Fix steps
    if extra.get('fix_steps'):
        lines.append(f"\n### Remediation Steps")
        for i, step in enumerate(extra['fix_steps'], 1):
            lines.append(f"  {i}. {step}")
    elif finding.remediation:
        lines.append(f"\n### Remediation")
        lines.append(f"  • {finding.remediation}")

    return "\n".join(lines)


def format_executive_summary(
    findings: List[Finding],
    scan_url: str,
    scan_date: datetime,
    pages_scanned: int,
) -> str:
    """Generate executive summary in Real-Time-Examples style."""

    # Count by severity
    severity_counts = {
        FindingSeverity.CRITICAL: 0,
        FindingSeverity.HIGH: 0,
        FindingSeverity.MEDIUM: 0,
        FindingSeverity.LOW: 0,
        FindingSeverity.INFO: 0,
    }
    for f in findings:
        severity_counts[f.severity] = severity_counts.get(f.severity, 0) + 1

    # Calculate score (simple formula: 100 - (critical*20 + high*10 + medium*5 + low*2))
    score = max(0, 100 - (
        severity_counts[FindingSeverity.CRITICAL] * 20 +
        severity_counts[FindingSeverity.HIGH] * 10 +
        severity_counts[FindingSeverity.MEDIUM] * 5 +
        severity_counts[FindingSeverity.LOW] * 2
    ))

    # Risk level
    if score >= 85:
        risk_level = "GREEN"
        risk_bar = "████████████████████"
    elif score >= 60:
        risk_level = "AMBER"
        risk_bar = "████████████████░░░░"
    else:
        risk_level = "RED"
        risk_bar = "████████░░░░░░░░░░░░"

    # Penalty exposure calculation
    penalty = 0
    if severity_counts[FindingSeverity.CRITICAL] > 0:
        penalty += 250  # ₹250 crore for critical
    if severity_counts[FindingSeverity.HIGH] > 0:
        penalty += 50  # ₹50 crore for high
    if severity_counts[FindingSeverity.MEDIUM] > 0:
        penalty += 10  # ₹10 crore for medium

    # Group critical findings by type
    critical_findings = [f for f in findings if f.severity == FindingSeverity.CRITICAL]
    high_findings = [f for f in findings if f.severity == FindingSeverity.HIGH]
    medium_findings = [f for f in findings if f.severity == FindingSeverity.MEDIUM]
    low_findings = [f for f in findings if f.severity == FindingSeverity.LOW]

    summary = f"""
┌─────────────────────────────────────────────────────────────┐
│                                                              │
│     DPDP COMPLIANCE AUDIT REPORT - EXECUTIVE SUMMARY        │
│                                                              │
│     Application: {scan_url[:42]:<42} │
│     Audit Date: {scan_date.strftime('%B %d, %Y'):<43} │
│     Auditor: DPDP GUI Compliance Scanner v1.0               │
│                                                              │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  OVERALL COMPLIANCE SCORE                                    │
│                                                              │
│         ┌────────────────────────────────────┐              │
│         │                                    │              │
│         │            {score:>3} / 100                │              │
│         │                                    │              │
│         │         {risk_bar}       │              │
│         │                                    │              │
│         │          RISK LEVEL: {risk_level:<4}           │              │
│         │                                    │              │
│         └────────────────────────────────────┘              │
│                                                              │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  SCAN STATISTICS                                             │
│                                                              │
│  Pages Scanned:     {pages_scanned:<5}                                  │
│  Total Findings:    {len(findings):<5}                                  │
│  Critical Issues:   {severity_counts[FindingSeverity.CRITICAL]:<5}                                  │
│  High Issues:       {severity_counts[FindingSeverity.HIGH]:<5}                                  │
│  Medium Issues:     {severity_counts[FindingSeverity.MEDIUM]:<5}                                  │
│  Low Issues:        {severity_counts[FindingSeverity.LOW]:<5}                                  │
│                                                              │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  CRITICAL FINDINGS                                           │
│                                                              │"""

    if critical_findings:
        summary += f"\n│  🔴 {len(critical_findings)} CRITICAL Issues (Immediate action required)           │"
        for f in critical_findings[:5]:
            title = f.title[:50] + "..." if len(f.title) > 50 else f.title
            summary += f"\n│     • {title:<52} │"
    else:
        summary += f"\n│  ✓ No critical issues found                              │"

    summary += f"""
│                                                              │
│  HIGH ISSUES                                                 │
│                                                              │"""

    if high_findings:
        summary += f"\n│  🟠 {len(high_findings)} HIGH Issues (Action within 30 days)                   │"
        for f in high_findings[:5]:
            title = f.title[:50] + "..." if len(f.title) > 50 else f.title
            summary += f"\n│     • {title:<52} │"
    else:
        summary += f"\n│  ✓ No high severity issues found                         │"

    summary += f"""
│                                                              │
│  🟡 {len(medium_findings)} MEDIUM Issues (Action within 60 days)                │
│  🟢 {len(low_findings)} LOW Issues (Best practice improvements)               │
│                                                              │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  PENALTY EXPOSURE                                            │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ Violation Category          │ Max Penalty          │    │
│  ├─────────────────────────────┼──────────────────────┤    │
│  │ Security Safeguards (8.5)   │ ₹250 crore          │    │
│  │ Children's Data (9)         │ ₹200 crore          │    │
│  │ Consent Violations (6)      │ ₹50 crore           │    │
│  │ Other Violations            │ ₹50 crore           │    │
│  ├─────────────────────────────┼──────────────────────┤    │
│  │ ESTIMATED TOTAL EXPOSURE    │ ₹{penalty:<3} crore          │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  RECOMMENDED ACTIONS                                         │
│                                                              │
│  IMMEDIATE (This Week):                                      │"""

    # Add immediate actions based on critical findings
    if critical_findings:
        for f in critical_findings[:3]:
            action = f.remediation[:45] + "..." if f.remediation and len(f.remediation) > 45 else (f.remediation or "Review and fix")
            summary += f"\n│  □ {action:<55} │"
    else:
        summary += f"\n│  ✓ No immediate actions required                         │"

    summary += f"""
│                                                              │
│  SHORT-TERM (30 Days):                                       │"""

    if high_findings:
        for f in high_findings[:3]:
            action = f.remediation[:45] + "..." if f.remediation and len(f.remediation) > 45 else (f.remediation or "Review and fix")
            summary += f"\n│  □ {action:<55} │"
    else:
        summary += f"\n│  ✓ No short-term actions required                        │"

    summary += f"""
│                                                              │
└─────────────────────────────────────────────────────────────┘
"""

    return summary


def generate_detailed_report(
    findings: List[Finding],
    scan_url: str,
    scan_date: datetime,
    pages_scanned: int,
) -> str:
    """Generate complete detailed report."""

    report_parts = []

    # Executive Summary
    report_parts.append("# DPDP GUI Compliance Audit Report")
    report_parts.append(f"\n**Scan URL:** {scan_url}")
    report_parts.append(f"**Scan Date:** {scan_date.strftime('%Y-%m-%d %H:%M:%S')}")
    report_parts.append(f"**Pages Scanned:** {pages_scanned}")
    report_parts.append(f"**Total Findings:** {len(findings)}")

    # Executive Summary Box
    report_parts.append("\n## Executive Summary\n")
    report_parts.append("```")
    report_parts.append(format_executive_summary(findings, scan_url, scan_date, pages_scanned))
    report_parts.append("```")

    # Detailed Findings Section
    report_parts.append("\n## Detailed Findings\n")

    # Group by severity
    critical = [f for f in findings if f.severity == FindingSeverity.CRITICAL]
    high = [f for f in findings if f.severity == FindingSeverity.HIGH]
    medium = [f for f in findings if f.severity == FindingSeverity.MEDIUM]
    low = [f for f in findings if f.severity == FindingSeverity.LOW]

    idx = 1

    if critical:
        report_parts.append("\n### 🔴 Critical Findings\n")
        for f in critical:
            report_parts.append(format_finding_detailed(f, idx))
            idx += 1

    if high:
        report_parts.append("\n### 🟠 High Severity Findings\n")
        for f in high:
            report_parts.append(format_finding_detailed(f, idx))
            idx += 1

    if medium:
        report_parts.append("\n### 🟡 Medium Severity Findings\n")
        for f in medium:
            report_parts.append(format_finding_detailed(f, idx))
            idx += 1

    if low:
        report_parts.append("\n### 🟢 Low Severity Findings\n")
        for f in low:
            report_parts.append(format_finding_detailed(f, idx))
            idx += 1

    # Appendix - By Page
    report_parts.append("\n## Appendix: Findings by Page\n")

    findings_by_page: Dict[str, List[Finding]] = {}
    for f in findings:
        page_url = f.location or "Unknown"
        if page_url not in findings_by_page:
            findings_by_page[page_url] = []
        findings_by_page[page_url].append(f)

    for page_url, page_findings in findings_by_page.items():
        report_parts.append(f"\n### {page_url}\n")
        report_parts.append(f"| # | Title | Severity | DPDP Section |")
        report_parts.append(f"|---|-------|----------|--------------|")
        for i, f in enumerate(page_findings, 1):
            title = f.title[:40] + "..." if len(f.title) > 40 else f.title
            report_parts.append(f"| {i} | {title} | {get_severity_icon(f.severity)} {f.severity.value} | {f.dpdp_section or 'N/A'} |")

    # Footer
    report_parts.append(f"""
---

**Report Generated By:** DPDP GUI Compliance Scanner v1.0
**Report Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

*This report provides an assessment of DPDP compliance based on automated scanning.
Manual review is recommended for comprehensive compliance verification.*
""")

    return "\n".join(report_parts)


def generate_pagewise_findings(
    findings: List[Finding],
) -> Dict[str, List[Dict[str, Any]]]:
    """Generate findings grouped by page for frontend display."""

    findings_by_page: Dict[str, List[Dict[str, Any]]] = {}

    for f in findings:
        page_url = f.location or "Unknown"

        if page_url not in findings_by_page:
            findings_by_page[page_url] = []

        finding_data = {
            "id": str(f.id) if hasattr(f, 'id') else None,
            "title": f.title,
            "description": f.description,
            "severity": f.severity.value,
            "severity_icon": get_severity_icon(f.severity),
            "status": f.status.value,
            "check_type": f.check_type.value,
            "dpdp_section": f.dpdp_section,
            "remediation": f.remediation,
            "element_selector": f.element_selector,
            "penalty_risk": get_penalty_risk(f.severity, f.check_type),
        }

        # Add extra_data if available
        if f.extra_data:
            finding_data["extra_data"] = f.extra_data

            # Extract key fields from extra_data for easier access
            if f.extra_data.get("code_before"):
                finding_data["code_before"] = f.extra_data["code_before"]
            if f.extra_data.get("code_after"):
                finding_data["code_after"] = f.extra_data["code_after"]
            if f.extra_data.get("visual_representation"):
                finding_data["visual_representation"] = f.extra_data["visual_representation"]
            if f.extra_data.get("fix_steps"):
                finding_data["fix_steps"] = f.extra_data["fix_steps"]
            if f.extra_data.get("dpdp_reference"):
                finding_data["dpdp_reference"] = f.extra_data["dpdp_reference"]

        findings_by_page[page_url].append(finding_data)

    return findings_by_page
