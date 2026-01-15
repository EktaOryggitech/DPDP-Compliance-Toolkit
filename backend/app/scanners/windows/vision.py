"""
DPDP GUI Compliance Scanner - Windows Vision Module

Integrates OpenCV and Tesseract OCR for Windows application scanning.
"""
import asyncio
import io
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import tempfile

# Conditional imports for Windows
try:
    import cv2
    import numpy as np
    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False
    cv2 = None
    np = None

try:
    import pytesseract
    from PIL import Image
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False
    pytesseract = None
    Image = None

from app.core.config import settings


@dataclass
class OCRResult:
    """Result of OCR text extraction."""
    text: str
    confidence: float
    language: str
    words: List[Dict[str, Any]] = field(default_factory=list)
    lines: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class UIElement:
    """Detected UI element from vision analysis."""
    element_type: str  # button, checkbox, text, input, link, etc.
    text: str
    bounding_box: Tuple[int, int, int, int]  # x, y, width, height
    confidence: float
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class VisionAnalysisResult:
    """Complete vision analysis result."""
    ocr_result: OCRResult
    detected_elements: List[UIElement]
    consent_elements: List[UIElement]
    dark_pattern_indicators: List[Dict[str, Any]]
    screenshot_path: Optional[str] = None


class WindowsVisionAnalyzer:
    """
    Vision-based analyzer for Windows applications.

    Uses:
    - OpenCV for image processing and UI element detection
    - Tesseract OCR for text extraction (English + Hindi)
    - Heuristics for consent element and dark pattern detection
    """

    def __init__(self):
        if not OPENCV_AVAILABLE:
            raise RuntimeError("OpenCV (cv2) is required for vision analysis")
        if not TESSERACT_AVAILABLE:
            raise RuntimeError("pytesseract is required for OCR")

        # Configure Tesseract path if on Windows
        if sys.platform == "win32" and hasattr(settings, "TESSERACT_CMD"):
            tesseract_cmd = getattr(settings, "TESSERACT_CMD", None)
            if tesseract_cmd and os.path.exists(tesseract_cmd):
                pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

        # UI element detection colors (BGR format)
        self.button_colors = [
            (66, 133, 244),   # Blue
            (52, 168, 83),    # Green
            (234, 67, 53),    # Red
            (251, 188, 5),    # Yellow
        ]

    async def analyze_screenshot(
        self,
        screenshot_path: str,
        languages: List[str] = None,
    ) -> VisionAnalysisResult:
        """
        Analyze a screenshot using OCR and computer vision.

        Args:
            screenshot_path: Path to the screenshot image
            languages: OCR languages (default: ['eng', 'hin'])

        Returns:
            VisionAnalysisResult with extracted text and detected elements
        """
        languages = languages or ["eng", "hin"]

        def _analyze():
            # Load image
            image = cv2.imread(screenshot_path)
            if image is None:
                raise ValueError(f"Could not load image: {screenshot_path}")

            # Perform OCR
            ocr_result = self._perform_ocr(image, languages)

            # Detect UI elements
            detected_elements = self._detect_ui_elements(image)

            # Find consent-related elements
            consent_elements = self._find_consent_elements(
                detected_elements, ocr_result.text
            )

            # Detect dark pattern indicators
            dark_patterns = self._detect_dark_patterns(
                image, detected_elements, ocr_result.text
            )

            return VisionAnalysisResult(
                ocr_result=ocr_result,
                detected_elements=detected_elements,
                consent_elements=consent_elements,
                dark_pattern_indicators=dark_patterns,
                screenshot_path=screenshot_path,
            )

        return await asyncio.to_thread(_analyze)

    def _perform_ocr(self, image: np.ndarray, languages: List[str]) -> OCRResult:
        """Perform OCR on the image."""
        # Convert to RGB for PIL
        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(rgb_image)

        # Configure Tesseract
        lang_str = "+".join(languages)

        # Get detailed OCR data
        ocr_data = pytesseract.image_to_data(
            pil_image,
            lang=lang_str,
            output_type=pytesseract.Output.DICT,
        )

        # Get plain text
        text = pytesseract.image_to_string(pil_image, lang=lang_str)

        # Extract words with confidence
        words = []
        lines = []
        current_line = []
        current_line_num = -1

        n_boxes = len(ocr_data["text"])
        confidences = []

        for i in range(n_boxes):
            word_text = ocr_data["text"][i].strip()
            conf = int(ocr_data["conf"][i])

            if word_text and conf > 0:
                word_info = {
                    "text": word_text,
                    "confidence": conf,
                    "x": ocr_data["left"][i],
                    "y": ocr_data["top"][i],
                    "width": ocr_data["width"][i],
                    "height": ocr_data["height"][i],
                }
                words.append(word_info)
                confidences.append(conf)

                # Track lines
                line_num = ocr_data["line_num"][i]
                if line_num != current_line_num:
                    if current_line:
                        lines.append({
                            "text": " ".join(w["text"] for w in current_line),
                            "words": current_line.copy(),
                        })
                    current_line = [word_info]
                    current_line_num = line_num
                else:
                    current_line.append(word_info)

        if current_line:
            lines.append({
                "text": " ".join(w["text"] for w in current_line),
                "words": current_line,
            })

        avg_confidence = sum(confidences) / len(confidences) if confidences else 0

        # Detect primary language
        detected_lang = "eng"
        hindi_pattern = any(ord(c) >= 0x0900 and ord(c) <= 0x097F for c in text)
        if hindi_pattern:
            detected_lang = "hin" if text.count("।") > text.count(".") else "mixed"

        return OCRResult(
            text=text,
            confidence=avg_confidence,
            language=detected_lang,
            words=words,
            lines=lines,
        )

    def _detect_ui_elements(self, image: np.ndarray) -> List[UIElement]:
        """Detect UI elements in the image using computer vision."""
        elements = []

        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Detect edges
        edges = cv2.Canny(gray, 50, 150)

        # Find contours
        contours, _ = cv2.findContours(
            edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        # Analyze each contour
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)

            # Filter out very small or very large regions
            if w < 20 or h < 10 or w > image.shape[1] * 0.9:
                continue

            # Determine element type based on aspect ratio and size
            aspect_ratio = w / h if h > 0 else 0
            area = w * h

            element_type = self._classify_element(
                image, x, y, w, h, aspect_ratio, area
            )

            if element_type:
                # Extract text from this region using OCR
                roi = image[y:y+h, x:x+w]
                element_text = self._extract_roi_text(roi)

                elements.append(UIElement(
                    element_type=element_type,
                    text=element_text,
                    bounding_box=(x, y, w, h),
                    confidence=0.7,
                ))

        return elements

    def _classify_element(
        self,
        image: np.ndarray,
        x: int, y: int, w: int, h: int,
        aspect_ratio: float,
        area: int,
    ) -> Optional[str]:
        """Classify a UI element based on visual features."""
        # Extract region of interest
        roi = image[y:y+h, x:x+w]

        # Check for button-like appearance
        if 2 < aspect_ratio < 8 and 1000 < area < 50000:
            # Check if region has uniform color (button)
            hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
            h_hist = cv2.calcHist([hsv], [0], None, [180], [0, 180])
            if np.max(h_hist) > 0.5 * np.sum(h_hist):
                return "button"

        # Check for checkbox (small square)
        if 0.8 < aspect_ratio < 1.2 and 100 < area < 2000:
            return "checkbox"

        # Check for text input (horizontal rectangle)
        if aspect_ratio > 3 and h < 50 and w > 100:
            return "input"

        # Check for link (underlined text - detect blue color)
        mean_color = cv2.mean(roi)[:3]
        if mean_color[0] > 150 and mean_color[1] < 100 and mean_color[2] < 100:
            return "link"

        return None

    def _extract_roi_text(self, roi: np.ndarray) -> str:
        """Extract text from a region of interest."""
        try:
            rgb_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2RGB)
            pil_roi = Image.fromarray(rgb_roi)
            text = pytesseract.image_to_string(pil_roi, lang="eng+hin")
            return text.strip()
        except Exception:
            return ""

    def _find_consent_elements(
        self,
        elements: List[UIElement],
        ocr_text: str,
    ) -> List[UIElement]:
        """Find elements related to consent."""
        consent_keywords = [
            "consent", "agree", "accept", "i agree", "i accept",
            "privacy", "terms", "conditions", "policy",
            "checkbox", "opt-in", "opt-out", "subscribe",
            "सहमति", "स्वीकार", "मैं सहमत", "गोपनीयता", "शर्तें",
        ]

        consent_elements = []

        for element in elements:
            element_text_lower = element.text.lower()

            # Check if element text contains consent keywords
            if any(kw in element_text_lower for kw in consent_keywords):
                consent_elements.append(element)
                continue

            # Check if it's a checkbox near consent text
            if element.element_type == "checkbox":
                # Look for consent keywords in surrounding OCR text
                x, y, w, h = element.bounding_box
                nearby_text = self._get_nearby_text(ocr_text, y, h)
                if any(kw in nearby_text.lower() for kw in consent_keywords):
                    consent_elements.append(element)

        return consent_elements

    def _get_nearby_text(self, full_text: str, y: int, height: int) -> str:
        """Get text that might be near a given element (simplified)."""
        # This is a simplified version - in production, you'd use word bounding boxes
        lines = full_text.split("\n")
        return " ".join(lines)  # Return all text as simplified approach

    def _detect_dark_patterns(
        self,
        image: np.ndarray,
        elements: List[UIElement],
        ocr_text: str,
    ) -> List[Dict[str, Any]]:
        """Detect visual dark patterns in the UI."""
        dark_patterns = []

        # 1. Check for size asymmetry between accept/reject buttons
        accept_buttons = [e for e in elements if e.element_type == "button"
                        and any(kw in e.text.lower() for kw in ["accept", "agree", "yes", "ok"])]
        reject_buttons = [e for e in elements if e.element_type == "button"
                         and any(kw in e.text.lower() for kw in ["reject", "decline", "no", "cancel"])]

        if accept_buttons and reject_buttons:
            accept_area = max(b.bounding_box[2] * b.bounding_box[3] for b in accept_buttons)
            reject_area = max(b.bounding_box[2] * b.bounding_box[3] for b in reject_buttons)

            if accept_area > reject_area * 2:
                dark_patterns.append({
                    "type": "visual_asymmetry",
                    "description": "Accept button is significantly larger than reject button",
                    "severity": "high",
                })

        # 2. Check for color contrast issues (accept prominent, reject muted)
        for accept in accept_buttons:
            x, y, w, h = accept.bounding_box
            if y + h <= image.shape[0] and x + w <= image.shape[1]:
                roi = image[y:y+h, x:x+w]
                mean_color = cv2.mean(roi)[:3]

                # Check if accept button has bright/saturated color
                hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
                saturation = np.mean(hsv[:, :, 1])
                value = np.mean(hsv[:, :, 2])

                if saturation > 100 and value > 150:
                    # Bright colored accept button
                    for reject in reject_buttons:
                        rx, ry, rw, rh = reject.bounding_box
                        if ry + rh <= image.shape[0] and rx + rw <= image.shape[1]:
                            reject_roi = image[ry:ry+rh, rx:rx+rw]
                            reject_hsv = cv2.cvtColor(reject_roi, cv2.COLOR_BGR2HSV)
                            reject_sat = np.mean(reject_hsv[:, :, 1])

                            if reject_sat < 50:
                                dark_patterns.append({
                                    "type": "color_manipulation",
                                    "description": "Accept button is colorful while reject is muted/gray",
                                    "severity": "medium",
                                })
                                break

        # 3. Check for very small text (potential hidden info)
        for element in elements:
            if element.bounding_box[3] < 12:  # Height less than 12 pixels
                if any(kw in element.text.lower() for kw in
                       ["consent", "data", "share", "agree", "terms"]):
                    dark_patterns.append({
                        "type": "hidden_information",
                        "description": f"Important text in very small font: {element.text[:50]}",
                        "severity": "high",
                    })

        # 4. Check for pre-selected checkboxes (based on fill color)
        for element in elements:
            if element.element_type == "checkbox":
                x, y, w, h = element.bounding_box
                if y + h <= image.shape[0] and x + w <= image.shape[1]:
                    roi = image[y:y+h, x:x+w]

                    # Check if checkbox appears filled (dark center)
                    gray_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
                    center_region = gray_roi[h//4:3*h//4, w//4:3*w//4]

                    if center_region.size > 0 and np.mean(center_region) < 128:
                        dark_patterns.append({
                            "type": "pre_checked",
                            "description": f"Checkbox appears pre-selected: {element.text[:50]}",
                            "severity": "critical",
                            "bounding_box": element.bounding_box,
                        })

        return dark_patterns

    async def capture_window_screenshot(
        self,
        window_handle: int,
        output_path: Optional[str] = None,
    ) -> str:
        """Capture screenshot of a specific window."""
        if sys.platform != "win32":
            raise RuntimeError("Window capture only supported on Windows")

        def _capture():
            import win32gui
            import win32ui
            import win32con
            from ctypes import windll

            # Get window dimensions
            left, top, right, bottom = win32gui.GetWindowRect(window_handle)
            width = right - left
            height = bottom - top

            # Create device contexts
            hwnd_dc = win32gui.GetWindowDC(window_handle)
            mfc_dc = win32ui.CreateDCFromHandle(hwnd_dc)
            save_dc = mfc_dc.CreateCompatibleDC()

            # Create bitmap
            save_bitmap = win32ui.CreateBitmap()
            save_bitmap.CreateCompatibleBitmap(mfc_dc, width, height)
            save_dc.SelectObject(save_bitmap)

            # Copy window content
            result = windll.user32.PrintWindow(window_handle, save_dc.GetSafeHdc(), 2)

            # Convert to numpy array
            bmp_info = save_bitmap.GetInfo()
            bmp_bits = save_bitmap.GetBitmapBits(True)

            img = np.frombuffer(bmp_bits, dtype=np.uint8)
            img = img.reshape((bmp_info["bmHeight"], bmp_info["bmWidth"], 4))

            # Convert BGRA to BGR
            img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

            # Cleanup
            win32gui.DeleteObject(save_bitmap.GetHandle())
            save_dc.DeleteDC()
            mfc_dc.DeleteDC()
            win32gui.ReleaseDC(window_handle, hwnd_dc)

            # Save to file
            if output_path:
                cv2.imwrite(output_path, img)
                return output_path
            else:
                temp_path = tempfile.mktemp(suffix=".png")
                cv2.imwrite(temp_path, img)
                return temp_path

        return await asyncio.to_thread(_capture)
