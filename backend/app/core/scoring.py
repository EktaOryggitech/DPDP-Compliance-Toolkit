"""
DPDP Compliance Scoring Module

Calculates compliance scores based on:
1. DPDP section penalty weights (actual penalty amounts in Crores)
2. Finding severity levels
3. Normalization by pages/windows scanned
"""
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass


# DPDP Section Penalties (in Crores as per DPDP Act 2023)
SECTION_PENALTIES = {
    # Section 5: Notice - Up to 50 Crore
    "Section 5": 50,
    "Section 5(1)": 50,
    "Section 5(2)": 50,

    # Section 6: Consent - Up to 50 Crore
    "Section 6": 50,
    "Section 6(1)": 50,
    "Section 6(3)": 50,
    "Section 6(4)": 50,
    "Section 6(5)": 50,
    "Section 6(6)": 50,  # Consent withdrawal
    "Section 6(7)": 50,

    # Section 7: Deemed Consent - Up to 50 Crore
    "Section 7": 50,

    # Section 8: Data Retention - Up to 50 Crore
    "Section 8": 50,
    "Section 8(3)": 50,
    "Section 8(7)": 50,

    # Section 9: Children's Data - Up to 200 Crore (HIGHEST PENALTY)
    "Section 9": 200,
    "Section 9(1)": 200,
    "Section 9(2)": 200,
    "Section 9(3)": 200,
    "Section 9(4)": 200,

    # Section 10: Significant Data Fiduciary - Up to 50 Crore
    "Section 10": 50,

    # Section 11: Data Principal Rights - Up to 50 Crore
    "Section 11": 50,
    "Section 11(1)": 50,
    "Section 11(2)": 50,
    "Section 11(3)": 50,

    # Section 12: Right to Correction/Erasure - Up to 50 Crore
    "Section 12": 50,
    "Section 12(1)": 50,
    "Section 12(2)": 50,

    # Section 13: Grievance Redressal - Up to 50 Crore
    "Section 13": 50,
    "Section 13(1)": 50,
    "Section 13(2)": 50,

    # Section 15: Data Breach - Up to 200 Crore
    "Section 15": 200,

    # Section 16: Government Data - Up to 50 Crore
    "Section 16": 50,

    # Section 17: Cross-border Transfer - Up to 50 Crore
    "Section 17": 50,

    # Section 18: Dark Patterns - Up to 50 Crore (as per CCPA guidelines)
    "Section 18": 50,

    # Default for unspecified sections
    "Other": 25,
}

# Severity multipliers - how much of the section penalty applies
SEVERITY_MULTIPLIERS = {
    "critical": 1.0,    # 100% of section penalty
    "high": 0.6,        # 60% of section penalty
    "medium": 0.3,      # 30% of section penalty
    "low": 0.1,         # 10% of section penalty
    "info": 0.0,        # Informational - no penalty
}

# Maximum possible penalty points (sum of all unique section penalties)
# Used for normalization
MAX_SECTION_PENALTY = 200  # Highest single section penalty (Section 9 or 15)


@dataclass
class SectionScore:
    """Score breakdown for a single DPDP section."""
    section: str
    section_name: str
    penalty_crores: int
    findings_count: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    section_score: float  # 0-100 for this section
    status: str  # "pass", "warning", "fail"


@dataclass
class ComplianceScoreResult:
    """Complete compliance score result."""
    overall_score: float
    grade: str
    risk_level: str
    penalty_exposure: str  # Estimated penalty exposure
    section_scores: List[SectionScore]
    summary: Dict[str, Any]


def get_section_penalty(dpdp_section: str) -> int:
    """Get the penalty amount for a DPDP section."""
    if not dpdp_section:
        return SECTION_PENALTIES["Other"]

    # Try exact match first
    if dpdp_section in SECTION_PENALTIES:
        return SECTION_PENALTIES[dpdp_section]

    # Try to match parent section (e.g., "Section 9(1)" -> "Section 9")
    for key in SECTION_PENALTIES:
        if dpdp_section.startswith(key):
            return SECTION_PENALTIES[key]

    # Check if section number is mentioned
    import re
    match = re.search(r'Section\s*(\d+)', dpdp_section)
    if match:
        section_num = f"Section {match.group(1)}"
        if section_num in SECTION_PENALTIES:
            return SECTION_PENALTIES[section_num]

    return SECTION_PENALTIES["Other"]


def get_severity_multiplier(severity: str) -> float:
    """Get the severity multiplier."""
    return SEVERITY_MULTIPLIERS.get(severity.lower(), 0.3)


def calculate_compliance_score(
    findings: List[Any],
    pages_scanned: int,
    return_detailed: bool = False
) -> ComplianceScoreResult | float:
    """
    Calculate DPDP compliance score based on findings.

    The scoring algorithm:
    1. Groups findings by DPDP section
    2. Calculates penalty points based on section penalty × severity multiplier
    3. Normalizes by pages scanned to be fair to larger sites
    4. Converts to a 0-100 score

    Args:
        findings: List of finding objects with severity and dpdp_section
        pages_scanned: Number of pages/windows scanned
        return_detailed: If True, returns full ComplianceScoreResult, else just score

    Returns:
        ComplianceScoreResult or float score (0-100)
    """
    if not findings:
        # Perfect score if no findings
        if return_detailed:
            return ComplianceScoreResult(
                overall_score=100.0,
                grade="A+",
                risk_level="Minimal",
                penalty_exposure="None",
                section_scores=[],
                summary={
                    "total_findings": 0,
                    "pages_scanned": pages_scanned,
                    "findings_per_page": 0,
                }
            )
        return 100.0

    # Group findings by section
    section_findings: Dict[str, List[Any]] = {}
    for finding in findings:
        section = getattr(finding, 'dpdp_section', None) or "Other"
        if section not in section_findings:
            section_findings[section] = []
        section_findings[section].append(finding)

    # Calculate penalty points per section
    total_penalty_points = 0
    section_scores = []
    max_penalty_exposure = 0

    for section, section_findings_list in section_findings.items():
        section_penalty = get_section_penalty(section)
        section_points = 0

        critical = high = medium = low = 0

        for finding in section_findings_list:
            severity = getattr(finding, 'severity', None)
            if severity:
                severity_str = severity.value if hasattr(severity, 'value') else str(severity)
                multiplier = get_severity_multiplier(severity_str)
                section_points += section_penalty * multiplier

                # Count by severity
                severity_lower = severity_str.lower()
                if severity_lower == "critical":
                    critical += 1
                elif severity_lower == "high":
                    high += 1
                elif severity_lower == "medium":
                    medium += 1
                elif severity_lower == "low":
                    low += 1

        total_penalty_points += section_points

        # Track max penalty exposure (worst case if all findings are critical)
        if critical > 0 or high > 0:
            max_penalty_exposure = max(max_penalty_exposure, section_penalty)

        # Calculate section score (0-100)
        # A section is "passing" if penalty points < 50% of max possible
        max_section_points = section_penalty * len(section_findings_list)
        if max_section_points > 0:
            section_score = max(0, 100 - (section_points / max_section_points * 100))
        else:
            section_score = 100

        # Determine section status
        if section_score >= 80:
            status = "pass"
        elif section_score >= 50:
            status = "warning"
        else:
            status = "fail"

        section_scores.append(SectionScore(
            section=section,
            section_name=get_section_name(section),
            penalty_crores=section_penalty,
            findings_count=len(section_findings_list),
            critical_count=critical,
            high_count=high,
            medium_count=medium,
            low_count=low,
            section_score=round(section_score, 1),
            status=status,
        ))

    # Normalize penalty points by pages scanned
    # This makes scoring fair: a site with 100 pages shouldn't be penalized
    # more than a site with 10 pages just because it has more surface area
    pages_factor = max(pages_scanned, 1)

    # Calculate findings density (findings per page)
    findings_density = len(findings) / pages_factor

    # Normalize penalty points
    # Base normalization: divide by pages, but cap the benefit
    # A site shouldn't get a pass just because it has many pages
    normalization_factor = min(pages_factor, 50) / 10  # Cap at 50 pages worth of normalization
    normalized_penalty = total_penalty_points / max(normalization_factor, 1)

    # Convert to score (0-100)
    # Scale factor determined by expected penalty range
    # With max section penalty of 200 and severity multiplier of 1.0,
    # a single critical finding in Section 9 = 200 points
    scale_factor = 500  # Tuned for reasonable score distribution

    raw_score = 100 - (normalized_penalty / scale_factor * 100)
    overall_score = max(0, min(100, raw_score))

    # Round to 1 decimal
    overall_score = round(overall_score, 1)

    # Determine grade
    grade = get_grade(overall_score)

    # Determine risk level
    risk_level = get_risk_level(overall_score, section_scores)

    # Estimate penalty exposure
    penalty_exposure = get_penalty_exposure(max_penalty_exposure, section_scores)

    # Count totals
    total_critical = sum(s.critical_count for s in section_scores)
    total_high = sum(s.high_count for s in section_scores)
    total_medium = sum(s.medium_count for s in section_scores)
    total_low = sum(s.low_count for s in section_scores)

    result = ComplianceScoreResult(
        overall_score=overall_score,
        grade=grade,
        risk_level=risk_level,
        penalty_exposure=penalty_exposure,
        section_scores=sorted(section_scores, key=lambda x: x.section_score),
        summary={
            "total_findings": len(findings),
            "critical_count": total_critical,
            "high_count": total_high,
            "medium_count": total_medium,
            "low_count": total_low,
            "pages_scanned": pages_scanned,
            "findings_per_page": round(findings_density, 2),
            "sections_assessed": len(section_scores),
            "sections_passing": sum(1 for s in section_scores if s.status == "pass"),
            "sections_warning": sum(1 for s in section_scores if s.status == "warning"),
            "sections_failing": sum(1 for s in section_scores if s.status == "fail"),
        }
    )

    if return_detailed:
        return result
    return overall_score


def get_grade(score: float) -> str:
    """Convert score to letter grade."""
    if score >= 95:
        return "A+"
    elif score >= 90:
        return "A"
    elif score >= 85:
        return "A-"
    elif score >= 80:
        return "B+"
    elif score >= 75:
        return "B"
    elif score >= 70:
        return "B-"
    elif score >= 65:
        return "C+"
    elif score >= 60:
        return "C"
    elif score >= 55:
        return "C-"
    elif score >= 50:
        return "D"
    else:
        return "F"


def get_risk_level(score: float, section_scores: List[SectionScore]) -> str:
    """Determine overall risk level."""
    # Check for critical findings in high-penalty sections
    high_penalty_critical = any(
        s.critical_count > 0 and s.penalty_crores >= 200
        for s in section_scores
    )

    if high_penalty_critical:
        return "Critical"

    total_critical = sum(s.critical_count for s in section_scores)
    total_high = sum(s.high_count for s in section_scores)

    if total_critical >= 3 or score < 40:
        return "Critical"
    elif total_critical >= 1 or total_high >= 5 or score < 60:
        return "High"
    elif total_high >= 2 or score < 75:
        return "Medium"
    elif score < 90:
        return "Low"
    else:
        return "Minimal"


def get_penalty_exposure(max_penalty: int, section_scores: List[SectionScore]) -> str:
    """Estimate potential penalty exposure."""
    if not section_scores:
        return "None"

    # Check for findings in high-penalty sections
    has_section_9_findings = any(
        "Section 9" in s.section and (s.critical_count > 0 or s.high_count > 0)
        for s in section_scores
    )

    has_section_15_findings = any(
        "Section 15" in s.section and (s.critical_count > 0 or s.high_count > 0)
        for s in section_scores
    )

    total_critical = sum(s.critical_count for s in section_scores)
    total_high = sum(s.high_count for s in section_scores)

    if has_section_9_findings or has_section_15_findings:
        return "Up to ₹200 Crore"
    elif total_critical >= 3:
        return "Up to ₹150 Crore"
    elif total_critical >= 1 or total_high >= 5:
        return "Up to ₹50 Crore"
    elif total_high >= 1:
        return "Up to ₹10 Crore"
    else:
        return "Minimal"


def get_section_name(section: str) -> str:
    """Get human-readable section name."""
    section_names = {
        "Section 5": "Notice to Data Principal",
        "Section 6": "Consent Requirements",
        "Section 7": "Deemed Consent",
        "Section 8": "Data Retention & Erasure",
        "Section 9": "Children's Data Protection",
        "Section 10": "Significant Data Fiduciary",
        "Section 11": "Data Principal Rights",
        "Section 12": "Right to Correction/Erasure",
        "Section 13": "Grievance Redressal",
        "Section 15": "Data Breach Notification",
        "Section 16": "Government Data Processing",
        "Section 17": "Cross-border Transfer",
        "Section 18": "Dark Patterns Prevention",
        "Other": "General Compliance",
    }

    # Try exact match
    if section in section_names:
        return section_names[section]

    # Try parent section
    import re
    match = re.search(r'Section\s*(\d+)', section)
    if match:
        parent = f"Section {match.group(1)}"
        if parent in section_names:
            return section_names[parent]

    return section


# Legacy function for backward compatibility
def calculate_simple_score(
    critical_count: int,
    high_count: int,
    medium_count: int,
    low_count: int
) -> float:
    """
    Simple scoring method (legacy).
    Kept for backward compatibility.
    """
    score = 100
    score -= critical_count * 15
    score -= high_count * 10
    score -= medium_count * 5
    score -= low_count * 2
    return max(0, float(score))
