"""
DPDP GUI Compliance Scanner - Evidence Annotator

Adds visual annotations to screenshots for compliance findings.
"""
import asyncio
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

from app.evidence.screenshot import AnnotatedScreenshot
from app.models.finding import FindingSeverity


@dataclass
class Annotation:
    """Single annotation on a screenshot."""
    type: str  # "rectangle", "highlight", "arrow", "text"
    coordinates: Tuple[int, int, int, int]  # x1, y1, x2, y2
    color: Tuple[int, int, int]  # RGB
    label: str
    severity: str
    finding_id: Optional[str] = None
    thickness: int = 2


class EvidenceAnnotator:
    """
    Annotates screenshots with visual markers for findings.

    Features:
    - Colored rectangles around problematic elements
    - Severity-based color coding
    - Text labels with finding descriptions
    - Arrow pointers
    - Highlight overlays
    """

    # Severity color mapping (RGB)
    SEVERITY_COLORS = {
        "critical": (220, 53, 69),    # Red
        "high": (253, 126, 20),       # Orange
        "medium": (255, 193, 7),      # Yellow
        "low": (40, 167, 69),         # Green
        "info": (23, 162, 184),       # Cyan
    }

    def __init__(self, font_path: str = None, font_size: int = 14):
        if not PIL_AVAILABLE:
            raise RuntimeError("PIL/Pillow is required for annotation")

        self.font_size = font_size

        # Try to load a font
        try:
            if font_path and os.path.exists(font_path):
                self.font = ImageFont.truetype(font_path, font_size)
            else:
                # Try common system fonts
                for font_name in ["arial.ttf", "Arial.ttf", "DejaVuSans.ttf"]:
                    try:
                        self.font = ImageFont.truetype(font_name, font_size)
                        break
                    except OSError:
                        continue
                else:
                    self.font = ImageFont.load_default()
        except Exception:
            self.font = ImageFont.load_default()

    async def annotate_screenshot(
        self,
        screenshot: AnnotatedScreenshot,
        annotations: List[Annotation],
        output_path: str = None,
    ) -> AnnotatedScreenshot:
        """
        Add annotations to a screenshot.

        Args:
            screenshot: Original screenshot
            annotations: List of annotations to add
            output_path: Optional output path (default: creates new file)

        Returns:
            Updated AnnotatedScreenshot with annotated_path set
        """
        def _annotate():
            # Load original image
            img = Image.open(screenshot.original_path)
            draw = ImageDraw.Draw(img, "RGBA")

            # Apply each annotation
            for annotation in annotations:
                self._apply_annotation(draw, img, annotation)

            # Create legend
            if annotations:
                img = self._add_legend(img, annotations)

            # Save annotated image
            if output_path:
                annotated_path = output_path
            else:
                base, ext = os.path.splitext(screenshot.original_path)
                annotated_path = f"{base}_annotated{ext}"

            img.save(annotated_path, "JPEG", quality=90)

            return annotated_path

        annotated_path = await asyncio.to_thread(_annotate)

        # Update screenshot object
        screenshot.annotated_path = annotated_path
        screenshot.annotations = [
            {
                "type": a.type,
                "coordinates": a.coordinates,
                "label": a.label,
                "severity": a.severity,
            }
            for a in annotations
        ]

        return screenshot

    def _apply_annotation(
        self,
        draw: "ImageDraw.Draw",
        img: "Image.Image",
        annotation: Annotation,
    ):
        """Apply a single annotation to the image."""
        x1, y1, x2, y2 = annotation.coordinates
        color = annotation.color

        if annotation.type == "rectangle":
            # Draw rectangle outline
            for i in range(annotation.thickness):
                draw.rectangle(
                    [x1 - i, y1 - i, x2 + i, y2 + i],
                    outline=color,
                )

            # Add semi-transparent fill
            overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
            overlay_draw = ImageDraw.Draw(overlay)
            overlay_draw.rectangle(
                [x1, y1, x2, y2],
                fill=(*color, 40),  # 40 alpha for light overlay
            )
            img.paste(Image.alpha_composite(img.convert("RGBA"), overlay))

        elif annotation.type == "highlight":
            # Yellow highlight overlay
            overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
            overlay_draw = ImageDraw.Draw(overlay)
            overlay_draw.rectangle(
                [x1, y1, x2, y2],
                fill=(255, 255, 0, 80),  # Yellow with transparency
            )
            img.paste(Image.alpha_composite(img.convert("RGBA"), overlay))

        elif annotation.type == "arrow":
            # Draw arrow pointing to the element
            self._draw_arrow(draw, x1, y1, x2, y2, color, annotation.thickness)

        elif annotation.type == "text":
            # Draw text label
            self._draw_label(draw, x1, y1, annotation.label, color)

        # Add label near the annotation
        if annotation.label and annotation.type in ["rectangle", "highlight"]:
            label_y = max(0, y1 - 20)
            self._draw_label(draw, x1, label_y, annotation.label, color)

    def _draw_arrow(
        self,
        draw: "ImageDraw.Draw",
        x1: int, y1: int,
        x2: int, y2: int,
        color: Tuple[int, int, int],
        thickness: int,
    ):
        """Draw an arrow from (x1, y1) to (x2, y2)."""
        import math

        # Main line
        draw.line([(x1, y1), (x2, y2)], fill=color, width=thickness)

        # Arrowhead
        angle = math.atan2(y2 - y1, x2 - x1)
        arrow_length = 15
        arrow_angle = math.pi / 6  # 30 degrees

        # Calculate arrowhead points
        left_x = x2 - arrow_length * math.cos(angle - arrow_angle)
        left_y = y2 - arrow_length * math.sin(angle - arrow_angle)
        right_x = x2 - arrow_length * math.cos(angle + arrow_angle)
        right_y = y2 - arrow_length * math.sin(angle + arrow_angle)

        draw.polygon(
            [(x2, y2), (left_x, left_y), (right_x, right_y)],
            fill=color,
        )

    def _draw_label(
        self,
        draw: "ImageDraw.Draw",
        x: int, y: int,
        text: str,
        color: Tuple[int, int, int],
    ):
        """Draw a text label with background."""
        # Get text bounding box
        bbox = draw.textbbox((x, y), text, font=self.font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        # Draw background
        padding = 4
        draw.rectangle(
            [x - padding, y - padding, x + text_width + padding, y + text_height + padding],
            fill=(255, 255, 255, 230),
            outline=color,
        )

        # Draw text
        draw.text((x, y), text, fill=color, font=self.font)

    def _add_legend(
        self,
        img: "Image.Image",
        annotations: List[Annotation],
    ) -> "Image.Image":
        """Add a legend showing annotation meanings."""
        # Get unique severities
        severities = list(set(a.severity for a in annotations))

        if not severities:
            return img

        # Create legend
        legend_height = 30 + len(severities) * 25
        legend_width = 200

        # Expand image to fit legend
        new_width = img.width
        new_height = img.height + legend_height

        new_img = Image.new("RGB", (new_width, new_height), (255, 255, 255))
        new_img.paste(img, (0, 0))

        draw = ImageDraw.Draw(new_img)

        # Draw legend box
        legend_x = 10
        legend_y = img.height + 5

        draw.rectangle(
            [legend_x, legend_y, legend_x + legend_width, new_height - 5],
            fill=(250, 250, 250),
            outline=(200, 200, 200),
        )

        # Draw title
        draw.text(
            (legend_x + 10, legend_y + 5),
            "Finding Severity:",
            fill=(0, 0, 0),
            font=self.font,
        )

        # Draw severity items
        y_offset = legend_y + 30
        for severity in severities:
            color = self.SEVERITY_COLORS.get(severity, (128, 128, 128))

            # Color box
            draw.rectangle(
                [legend_x + 10, y_offset, legend_x + 25, y_offset + 15],
                fill=color,
                outline=(0, 0, 0),
            )

            # Label
            draw.text(
                (legend_x + 35, y_offset),
                severity.capitalize(),
                fill=(0, 0, 0),
                font=self.font,
            )

            y_offset += 25

        return new_img

    def create_annotation_from_finding(
        self,
        finding: Dict[str, Any],
        element_box: Tuple[int, int, int, int],
    ) -> Annotation:
        """
        Create an annotation from a finding.

        Args:
            finding: Finding dict with severity, title, etc.
            element_box: (x, y, width, height) of the element

        Returns:
            Annotation object
        """
        severity = finding.get("severity", "medium").lower()
        color = self.SEVERITY_COLORS.get(severity, (128, 128, 128))

        x, y, w, h = element_box

        return Annotation(
            type="rectangle",
            coordinates=(x, y, x + w, y + h),
            color=color,
            label=finding.get("title", "Finding")[:50],
            severity=severity,
            finding_id=finding.get("id"),
            thickness=3 if severity in ["critical", "high"] else 2,
        )

    async def annotate_multiple(
        self,
        screenshot: AnnotatedScreenshot,
        findings: List[Dict[str, Any]],
    ) -> AnnotatedScreenshot:
        """
        Annotate a screenshot with multiple findings.

        Args:
            screenshot: Original screenshot
            findings: List of findings with element_box info

        Returns:
            Annotated screenshot
        """
        annotations = []

        for finding in findings:
            if "element_box" in finding:
                annotation = self.create_annotation_from_finding(
                    finding, finding["element_box"]
                )
                annotations.append(annotation)

        if annotations:
            return await self.annotate_screenshot(screenshot, annotations)

        return screenshot
