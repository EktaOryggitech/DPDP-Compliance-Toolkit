"""
DPDP GUI Compliance Scanner - PDF Report Generator

Generates professional PDF compliance reports using ReportLab.
"""
import io
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, Image, ListFlowable, ListItem, HRFlowable,
)
from reportlab.graphics.shapes import Drawing, Rect
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.charts.barcharts import VerticalBarChart

from app.models.scan import Scan
from app.models.finding import Finding
from app.models.application import Application


class PDFReportGenerator:
    """
    Generates professional PDF compliance reports.

    Report Structure:
    1. Cover Page with executive summary
    2. Compliance Score Overview
    3. Findings by DPDP Section
    4. Detailed Findings with evidence
    5. Remediation Recommendations
    6. Appendix with technical details
    """

    # Severity colors
    SEVERITY_COLORS = {
        "critical": colors.Color(0.86, 0.21, 0.27),  # Red
        "high": colors.Color(0.99, 0.49, 0.08),      # Orange
        "medium": colors.Color(1.0, 0.76, 0.03),     # Yellow
        "low": colors.Color(0.16, 0.65, 0.27),       # Green
    }

    def __init__(
        self,
        scan: Scan,
        application: Application,
        findings: List[Finding],
        include_evidence: bool = True,
    ):
        self.scan = scan
        self.application = application
        self.findings = findings
        self.include_evidence = include_evidence
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()

    def _setup_custom_styles(self):
        """Setup custom paragraph styles."""
        self.styles.add(ParagraphStyle(
            name="CoverTitle",
            parent=self.styles["Heading1"],
            fontSize=28,
            alignment=TA_CENTER,
            spaceAfter=30,
            textColor=colors.Color(0.05, 0.29, 0.53),  # Navy
        ))

        self.styles.add(ParagraphStyle(
            name="CoverSubtitle",
            parent=self.styles["Heading2"],
            fontSize=16,
            alignment=TA_CENTER,
            spaceAfter=20,
            textColor=colors.Color(0.4, 0.4, 0.4),
        ))

        self.styles.add(ParagraphStyle(
            name="SectionHeader",
            parent=self.styles["Heading2"],
            fontSize=16,
            spaceBefore=20,
            spaceAfter=10,
            textColor=colors.Color(0.05, 0.29, 0.53),
            borderWidth=1,
            borderColor=colors.Color(0.05, 0.29, 0.53),
            borderPadding=5,
        ))

        self.styles.add(ParagraphStyle(
            name="FindingTitle",
            parent=self.styles["Heading3"],
            fontSize=12,
            spaceBefore=10,
            spaceAfter=5,
        ))

        self.styles.add(ParagraphStyle(
            name="BodyJustified",
            parent=self.styles["BodyText"],
            alignment=TA_JUSTIFY,
        ))

    async def generate(self) -> io.BytesIO:
        """
        Generate the PDF report.

        Returns:
            BytesIO buffer containing the PDF
        """
        # Use data passed in during initialization
        scan = self.scan
        findings = self.findings
        application = self.application

        # Create PDF buffer
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72,
        )

        # Build story (content)
        story = []

        # 1. Cover Page
        story.extend(self._build_cover_page(scan, application))
        story.append(PageBreak())

        # 2. Executive Summary
        story.extend(self._build_executive_summary(scan, findings))
        story.append(PageBreak())

        # 3. Compliance Score Overview
        story.extend(self._build_score_overview(scan, findings))

        # 4. Findings by Section
        story.extend(self._build_findings_by_section(findings))

        # 5. Detailed Findings
        story.append(PageBreak())
        story.extend(self._build_detailed_findings(findings))

        # 6. Remediation Summary
        story.append(PageBreak())
        story.extend(self._build_remediation_summary(findings))

        # Build PDF
        doc.build(story, onFirstPage=self._add_header_footer,
                  onLaterPages=self._add_header_footer)

        buffer.seek(0)
        return buffer

    def _build_cover_page(
        self,
        scan: Scan,
        application: Application,
    ) -> List:
        """Build the cover page."""
        elements = []

        elements.append(Spacer(1, 2 * inch))

        # Title
        elements.append(Paragraph(
            "DPDP Compliance<br/>Audit Report",
            self.styles["CoverTitle"],
        ))

        elements.append(Spacer(1, 0.5 * inch))

        # Application name
        elements.append(Paragraph(
            f"<b>Application:</b> {application.name}",
            self.styles["CoverSubtitle"],
        ))

        if application.url:
            elements.append(Paragraph(
                f"{application.url}",
                self.styles["CoverSubtitle"],
            ))

        elements.append(Spacer(1, 0.5 * inch))

        # Scan details
        scan_date = scan.completed_at or scan.created_at
        elements.append(Paragraph(
            f"Scan Date: {scan_date.strftime('%B %d, %Y')}",
            self.styles["CoverSubtitle"],
        ))

        elements.append(Paragraph(
            f"Report Generated: {datetime.now().strftime('%B %d, %Y %H:%M')}",
            self.styles["CoverSubtitle"],
        ))

        elements.append(Spacer(1, 1 * inch))

        # Compliance score badge
        score = scan.overall_score or 0
        score_color = (
            colors.green if score >= 80 else
            colors.orange if score >= 60 else
            colors.red
        )

        elements.append(Paragraph(
            f"<font size='48' color='{score_color}'><b>{score}%</b></font>",
            ParagraphStyle("ScoreBadge", parent=self.styles["Normal"], alignment=TA_CENTER),
        ))
        elements.append(Paragraph(
            "Compliance Score",
            ParagraphStyle("ScoreLabel", parent=self.styles["Normal"], alignment=TA_CENTER),
        ))

        elements.append(Spacer(1, 2 * inch))

        # Footer note
        elements.append(Paragraph(
            "<i>This report is generated based on automated scanning and may require "
            "manual verification. It should be used as a guide for compliance assessment "
            "under the Digital Personal Data Protection Act, 2023.</i>",
            ParagraphStyle("FooterNote", parent=self.styles["Normal"],
                          alignment=TA_CENTER, fontSize=9, textColor=colors.gray),
        ))

        return elements

    def _build_executive_summary(
        self,
        scan: Scan,
        findings: List[Finding],
    ) -> List:
        """Build executive summary section."""
        elements = []

        elements.append(Paragraph("Executive Summary", self.styles["SectionHeader"]))
        elements.append(Spacer(1, 0.2 * inch))

        # Count by severity
        severity_counts = {
            "critical": 0, "high": 0, "medium": 0, "low": 0
        }
        for finding in findings:
            sev = finding.severity.value if hasattr(finding.severity, 'value') else str(finding.severity)
            if sev in severity_counts:
                severity_counts[sev] += 1

        # Summary paragraph
        summary_text = f"""
        This compliance audit was conducted on <b>{scan.pages_scanned}</b> pages/screens
        and identified <b>{len(findings)}</b> compliance findings. The overall compliance
        score is <b>{scan.overall_score or 0}%</b>.

        <br/><br/>
        <b>Finding Summary:</b>
        <br/>
        • Critical Issues: {severity_counts['critical']}<br/>
        • High Severity: {severity_counts['high']}<br/>
        • Medium Severity: {severity_counts['medium']}<br/>
        • Low Severity: {severity_counts['low']}
        """

        elements.append(Paragraph(summary_text, self.styles["BodyJustified"]))
        elements.append(Spacer(1, 0.3 * inch))

        # Key findings table
        elements.append(Paragraph("<b>Key Areas of Concern:</b>", self.styles["Normal"]))
        elements.append(Spacer(1, 0.1 * inch))

        # Group by section
        sections = {}
        for finding in findings:
            section = finding.dpdp_section or "Other"
            if section not in sections:
                sections[section] = 0
            sections[section] += 1

        table_data = [["DPDP Section", "Findings Count", "Status"]]
        for section, count in sorted(sections.items()):
            status = "Needs Attention" if count > 0 else "Compliant"
            status_color = "red" if count > 3 else "orange" if count > 0 else "green"
            table_data.append([
                section,
                str(count),
                Paragraph(f"<font color='{status_color}'>{status}</font>", self.styles["Normal"]),
            ])

        table = Table(table_data, colWidths=[2.5*inch, 1.5*inch, 2*inch])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.Color(0.05, 0.29, 0.53)),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 11),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
            ("BACKGROUND", (0, 1), (-1, -1), colors.Color(0.95, 0.95, 0.95)),
            ("GRID", (0, 0), (-1, -1), 1, colors.Color(0.8, 0.8, 0.8)),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 1), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 1), (-1, -1), 8),
        ]))

        elements.append(table)

        return elements

    def _build_score_overview(
        self,
        scan: Scan,
        findings: List[Finding],
    ) -> List:
        """Build compliance score visualization section."""
        elements = []

        elements.append(Spacer(1, 0.3 * inch))
        elements.append(Paragraph("Compliance Score Breakdown", self.styles["SectionHeader"]))
        elements.append(Spacer(1, 0.2 * inch))

        # Create pie chart for severity distribution
        severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for finding in findings:
            sev = finding.severity.value if hasattr(finding.severity, 'value') else str(finding.severity)
            if sev in severity_counts:
                severity_counts[sev] += 1

        if sum(severity_counts.values()) > 0:
            drawing = Drawing(400, 200)

            pie = Pie()
            pie.x = 100
            pie.y = 20
            pie.width = 150
            pie.height = 150
            pie.data = list(severity_counts.values())
            pie.labels = [f"{k.capitalize()}: {v}" for k, v in severity_counts.items()]
            pie.slices[0].fillColor = self.SEVERITY_COLORS["critical"]
            pie.slices[1].fillColor = self.SEVERITY_COLORS["high"]
            pie.slices[2].fillColor = self.SEVERITY_COLORS["medium"]
            pie.slices[3].fillColor = self.SEVERITY_COLORS["low"]

            drawing.add(pie)
            elements.append(drawing)

        return elements

    def _build_findings_by_section(self, findings: List[Finding]) -> List:
        """Build findings grouped by DPDP section."""
        elements = []

        elements.append(Spacer(1, 0.3 * inch))
        elements.append(Paragraph("Findings by DPDP Section", self.styles["SectionHeader"]))
        elements.append(Spacer(1, 0.2 * inch))

        # Group findings by section
        sections = {}
        for finding in findings:
            section = finding.dpdp_section or "Other"
            if section not in sections:
                sections[section] = []
            sections[section].append(finding)

        for section, section_findings in sorted(sections.items()):
            elements.append(Paragraph(
                f"<b>{section}</b> ({len(section_findings)} findings)",
                self.styles["Heading3"],
            ))

            # Summary table for this section
            table_data = [["Severity", "Title", "Page/Window"]]
            for f in section_findings[:5]:  # Limit to 5 per section in overview
                sev = f.severity.value if hasattr(f.severity, 'value') else str(f.severity)
                color = self.SEVERITY_COLORS.get(sev, colors.gray)
                table_data.append([
                    Paragraph(f"<font color='{color}'>{sev.upper()}</font>", self.styles["Normal"]),
                    f.title[:50] + "..." if len(f.title) > 50 else f.title,
                    (f.location or "")[:30] + "..." if f.location and len(f.location) > 30 else f.location or "",
                ])

            if len(section_findings) > 5:
                table_data.append(["", f"... and {len(section_findings) - 5} more", ""])

            table = Table(table_data, colWidths=[1*inch, 3*inch, 2*inch])
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.Color(0.9, 0.9, 0.9)),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.Color(0.8, 0.8, 0.8)),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]))

            elements.append(table)
            elements.append(Spacer(1, 0.2 * inch))

        return elements

    def _build_detailed_findings(self, findings: List[Finding]) -> List:
        """Build detailed findings section."""
        elements = []

        elements.append(Paragraph("Detailed Findings", self.styles["SectionHeader"]))
        elements.append(Spacer(1, 0.2 * inch))

        for i, finding in enumerate(findings, 1):
            sev = finding.severity.value if hasattr(finding.severity, 'value') else str(finding.severity)
            color = self.SEVERITY_COLORS.get(sev, colors.gray)

            # Finding header
            elements.append(Paragraph(
                f"<font color='{color}'>■</font> Finding #{i}: {finding.title}",
                self.styles["FindingTitle"],
            ))

            # Finding details table
            details = [
                ["Severity", sev.upper()],
                ["DPDP Section", finding.dpdp_section or "N/A"],
                ["Check Type", finding.check_type.value if hasattr(finding.check_type, 'value') else str(finding.check_type)],
                ["Page/Location", finding.location or "N/A"],
            ]

            details_table = Table(details, colWidths=[1.5*inch, 4.5*inch])
            details_table.setStyle(TableStyle([
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]))

            elements.append(details_table)

            # Description
            if finding.description:
                elements.append(Spacer(1, 0.1 * inch))
                elements.append(Paragraph(
                    f"<b>Description:</b> {finding.description}",
                    self.styles["Normal"],
                ))

            # Remediation
            if finding.remediation:
                elements.append(Spacer(1, 0.1 * inch))
                elements.append(Paragraph(
                    f"<b>Remediation:</b> {finding.remediation}",
                    self.styles["Normal"],
                ))

            elements.append(Spacer(1, 0.2 * inch))
            elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey))

        return elements

    def _build_remediation_summary(self, findings: List[Finding]) -> List:
        """Build remediation recommendations summary."""
        elements = []

        elements.append(Paragraph("Remediation Recommendations", self.styles["SectionHeader"]))
        elements.append(Spacer(1, 0.2 * inch))

        # Group remediations by priority
        critical_remediations = []
        high_remediations = []
        other_remediations = []

        for finding in findings:
            if finding.remediation:
                sev = finding.severity.value if hasattr(finding.severity, 'value') else str(finding.severity)
                item = f"{finding.title}: {finding.remediation}"

                if sev == "critical":
                    critical_remediations.append(item)
                elif sev == "high":
                    high_remediations.append(item)
                else:
                    other_remediations.append(item)

        if critical_remediations:
            elements.append(Paragraph(
                "<font color='red'><b>Critical Priority (Address Immediately):</b></font>",
                self.styles["Normal"],
            ))
            for rem in critical_remediations[:5]:
                elements.append(Paragraph(f"• {rem}", self.styles["Normal"]))
            elements.append(Spacer(1, 0.2 * inch))

        if high_remediations:
            elements.append(Paragraph(
                "<font color='orange'><b>High Priority (Address Within 30 Days):</b></font>",
                self.styles["Normal"],
            ))
            for rem in high_remediations[:5]:
                elements.append(Paragraph(f"• {rem}", self.styles["Normal"]))
            elements.append(Spacer(1, 0.2 * inch))

        if other_remediations:
            elements.append(Paragraph(
                "<b>Other Recommendations:</b>",
                self.styles["Normal"],
            ))
            for rem in other_remediations[:5]:
                elements.append(Paragraph(f"• {rem}", self.styles["Normal"]))

        return elements

    def _add_header_footer(self, canvas, doc):
        """Add header and footer to each page."""
        canvas.saveState()

        # Header
        canvas.setFont("Helvetica", 9)
        canvas.setFillColor(colors.gray)
        canvas.drawString(72, A4[1] - 50, "DPDP Compliance Report")
        canvas.drawRightString(A4[0] - 72, A4[1] - 50, f"Scan ID: {str(self.scan.id)[:8]}...")

        # Header line
        canvas.setStrokeColor(colors.Color(0.05, 0.29, 0.53))
        canvas.line(72, A4[1] - 55, A4[0] - 72, A4[1] - 55)

        # Footer
        canvas.setFont("Helvetica", 8)
        canvas.drawString(72, 40, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        canvas.drawCentredString(A4[0] / 2, 40, f"Page {doc.page}")
        canvas.drawRightString(A4[0] - 72, 40, "Confidential")

        # Footer line
        canvas.line(72, 55, A4[0] - 72, 55)

        canvas.restoreState()
