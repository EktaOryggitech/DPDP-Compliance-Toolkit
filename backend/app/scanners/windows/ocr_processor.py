"""
DPDP GUI Compliance Scanner - OCR Processor

Specialized OCR processing for Windows application text extraction.
"""
import asyncio
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

try:
    import pytesseract
    from PIL import Image, ImageEnhance, ImageFilter
    import cv2
    import numpy as np
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False


@dataclass
class ProcessedText:
    """Processed and cleaned OCR text result."""
    raw_text: str
    cleaned_text: str
    language: str
    confidence: float
    privacy_keywords: List[str] = field(default_factory=list)
    consent_phrases: List[str] = field(default_factory=list)
    pii_indicators: List[str] = field(default_factory=list)


class OCRProcessor:
    """
    Advanced OCR processor with preprocessing and post-processing.

    Features:
    - Image preprocessing for better OCR accuracy
    - Multi-language support (English + Hindi)
    - Privacy-focused keyword extraction
    - PII detection in extracted text
    """

    # Privacy-related keywords to extract
    PRIVACY_KEYWORDS = {
        "en": [
            "privacy", "consent", "personal data", "data protection",
            "terms", "conditions", "agree", "accept", "decline",
            "cookie", "tracking", "analytics", "third party",
            "share", "collect", "process", "storage", "retention",
            "delete", "erasure", "access", "correction", "withdraw",
            "grievance", "complaint", "data fiduciary", "data principal",
        ],
        "hi": [
            "गोपनीयता", "सहमति", "व्यक्तिगत डेटा", "डेटा संरक्षण",
            "शर्तें", "स्वीकार", "अस्वीकार", "कुकी", "ट्रैकिंग",
            "तृतीय पक्ष", "साझा", "एकत्र", "प्रसंस्करण",
            "संग्रहण", "विलोपन", "पहुंच", "सुधार", "शिकायत",
        ],
    }

    # Consent-related phrases
    CONSENT_PHRASES = [
        r"i\s+agree",
        r"i\s+accept",
        r"i\s+consent",
        r"by\s+(?:clicking|continuing|signing)",
        r"terms\s+(?:and|&)\s+conditions",
        r"privacy\s+policy",
        r"मैं\s+सहमत",
        r"मैं\s+स्वीकार",
    ]

    # PII patterns
    PII_PATTERNS = {
        "aadhaar": r"\b\d{4}\s?\d{4}\s?\d{4}\b",
        "pan": r"\b[A-Z]{5}[0-9]{4}[A-Z]\b",
        "phone": r"\b(?:\+91|0)?[6-9]\d{9}\b",
        "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
    }

    def __init__(self, tesseract_config: str = None):
        if not OCR_AVAILABLE:
            raise RuntimeError("OCR dependencies not available")

        self.tesseract_config = tesseract_config or "--oem 3 --psm 6"

    async def process_image(
        self,
        image_path: str,
        languages: List[str] = None,
        preprocess: bool = True,
    ) -> ProcessedText:
        """
        Process an image and extract text with analysis.

        Args:
            image_path: Path to the image file
            languages: OCR languages (default: ['eng', 'hin'])
            preprocess: Whether to preprocess image for better OCR

        Returns:
            ProcessedText with extracted and analyzed text
        """
        languages = languages or ["eng", "hin"]

        def _process():
            # Load image
            image = cv2.imread(image_path)
            if image is None:
                raise ValueError(f"Could not load image: {image_path}")

            # Preprocess if requested
            if preprocess:
                image = self._preprocess_image(image)

            # Perform OCR
            pil_image = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
            lang_str = "+".join(languages)

            # Get OCR text
            raw_text = pytesseract.image_to_string(
                pil_image,
                lang=lang_str,
                config=self.tesseract_config,
            )

            # Get confidence
            data = pytesseract.image_to_data(
                pil_image,
                lang=lang_str,
                output_type=pytesseract.Output.DICT,
            )
            confidences = [int(c) for c in data["conf"] if int(c) > 0]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0

            # Detect language
            detected_lang = self._detect_language(raw_text)

            # Clean text
            cleaned_text = self._clean_text(raw_text)

            # Extract privacy keywords
            privacy_keywords = self._extract_privacy_keywords(
                cleaned_text, detected_lang
            )

            # Find consent phrases
            consent_phrases = self._find_consent_phrases(cleaned_text)

            # Detect PII indicators
            pii_indicators = self._detect_pii(cleaned_text)

            return ProcessedText(
                raw_text=raw_text,
                cleaned_text=cleaned_text,
                language=detected_lang,
                confidence=avg_confidence,
                privacy_keywords=privacy_keywords,
                consent_phrases=consent_phrases,
                pii_indicators=pii_indicators,
            )

        return await asyncio.to_thread(_process)

    def _preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """Preprocess image for better OCR accuracy."""
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Apply adaptive thresholding
        binary = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 11, 2
        )

        # Denoise
        denoised = cv2.fastNlMeansDenoising(binary, None, 10, 7, 21)

        # Deskew if needed
        coords = np.column_stack(np.where(denoised > 0))
        if len(coords) > 0:
            angle = cv2.minAreaRect(coords)[-1]
            if angle < -45:
                angle = 90 + angle
            if abs(angle) > 0.5:
                (h, w) = denoised.shape[:2]
                center = (w // 2, h // 2)
                M = cv2.getRotationMatrix2D(center, angle, 1.0)
                denoised = cv2.warpAffine(
                    denoised, M, (w, h),
                    flags=cv2.INTER_CUBIC,
                    borderMode=cv2.BORDER_REPLICATE,
                )

        # Convert back to BGR for consistent handling
        return cv2.cvtColor(denoised, cv2.COLOR_GRAY2BGR)

    def _detect_language(self, text: str) -> str:
        """Detect the primary language of the text."""
        # Count Hindi Unicode characters
        hindi_chars = sum(1 for c in text if 0x0900 <= ord(c) <= 0x097F)
        english_chars = sum(1 for c in text if c.isalpha() and ord(c) < 128)

        total = hindi_chars + english_chars
        if total == 0:
            return "unknown"

        hindi_ratio = hindi_chars / total
        if hindi_ratio > 0.5:
            return "hi"
        elif hindi_ratio > 0.1:
            return "mixed"
        else:
            return "en"

    def _clean_text(self, text: str) -> str:
        """Clean and normalize OCR text."""
        # Remove excessive whitespace
        text = re.sub(r"\s+", " ", text)

        # Remove common OCR artifacts
        text = re.sub(r"[|\\]", "", text)

        # Normalize quotes
        text = text.replace("''", '"').replace("``", '"')

        # Remove isolated single characters (likely noise)
        text = re.sub(r"\s[a-zA-Z]\s", " ", text)

        return text.strip()

    def _extract_privacy_keywords(
        self, text: str, language: str
    ) -> List[str]:
        """Extract privacy-related keywords from text."""
        text_lower = text.lower()
        found_keywords = []

        # Check English keywords
        if language in ["en", "mixed"]:
            for keyword in self.PRIVACY_KEYWORDS["en"]:
                if keyword in text_lower:
                    found_keywords.append(keyword)

        # Check Hindi keywords
        if language in ["hi", "mixed"]:
            for keyword in self.PRIVACY_KEYWORDS["hi"]:
                if keyword in text:
                    found_keywords.append(keyword)

        return list(set(found_keywords))

    def _find_consent_phrases(self, text: str) -> List[str]:
        """Find consent-related phrases in text."""
        text_lower = text.lower()
        found_phrases = []

        for pattern in self.CONSENT_PHRASES:
            matches = re.findall(pattern, text_lower, re.IGNORECASE)
            found_phrases.extend(matches)

        return found_phrases

    def _detect_pii(self, text: str) -> List[str]:
        """Detect potential PII patterns in text."""
        pii_found = []

        for pii_type, pattern in self.PII_PATTERNS.items():
            if re.search(pattern, text, re.IGNORECASE):
                pii_found.append(pii_type)

        return pii_found

    async def process_multiple_images(
        self,
        image_paths: List[str],
        languages: List[str] = None,
    ) -> List[ProcessedText]:
        """Process multiple images concurrently."""
        tasks = [
            self.process_image(path, languages)
            for path in image_paths
        ]
        return await asyncio.gather(*tasks)

    async def extract_form_fields(
        self,
        image_path: str,
    ) -> List[Dict[str, Any]]:
        """
        Extract form field information from a screenshot.

        Detects input fields, labels, and their relationships.
        """
        def _extract():
            image = cv2.imread(image_path)
            if image is None:
                return []

            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

            # Find rectangular regions (potential input fields)
            edges = cv2.Canny(gray, 50, 150)
            contours, _ = cv2.findContours(
                edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )

            fields = []
            for contour in contours:
                x, y, w, h = cv2.boundingRect(contour)

                # Filter for input-field-like dimensions
                aspect_ratio = w / h if h > 0 else 0
                if aspect_ratio > 3 and 20 < h < 60 and w > 100:
                    # Extract text from region above (likely label)
                    label_region = image[max(0, y-30):y, x:x+w]
                    if label_region.size > 0:
                        pil_label = Image.fromarray(
                            cv2.cvtColor(label_region, cv2.COLOR_BGR2RGB)
                        )
                        label_text = pytesseract.image_to_string(
                            pil_label, lang="eng+hin"
                        ).strip()
                    else:
                        label_text = ""

                    # Extract text inside the field
                    field_region = image[y:y+h, x:x+w]
                    pil_field = Image.fromarray(
                        cv2.cvtColor(field_region, cv2.COLOR_BGR2RGB)
                    )
                    field_text = pytesseract.image_to_string(
                        pil_field, lang="eng+hin"
                    ).strip()

                    fields.append({
                        "type": "input",
                        "label": label_text,
                        "value": field_text,
                        "bounding_box": (x, y, w, h),
                        "is_empty": len(field_text) == 0,
                    })

            return fields

        return await asyncio.to_thread(_extract)
