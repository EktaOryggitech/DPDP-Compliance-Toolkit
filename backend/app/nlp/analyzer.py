"""
DPDP GUI Compliance Scanner - Text Analyzer

Uses spaCy for NLP analysis of English and Hindi text.
"""
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

import spacy
from spacy.language import Language

from app.core.config import settings


@dataclass
class EntityResult:
    """Named entity extraction result."""
    text: str
    label: str
    start: int
    end: int


@dataclass
class AnalysisResult:
    """Text analysis result."""
    language: str
    word_count: int
    sentence_count: int
    entities: List[EntityResult]
    pii_detected: List[Dict]
    keywords: List[str]
    sentiment: Optional[str] = None


class TextAnalyzer:
    """
    NLP text analyzer for DPDP compliance checking.

    Features:
    - Language detection (English/Hindi)
    - Named Entity Recognition (NER)
    - PII detection
    - Keyword extraction
    - Text preprocessing
    """

    # PII patterns for detection
    PII_PATTERNS = {
        "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
        "phone_india": r"\b(?:\+91|0)?[6-9]\d{9}\b",
        "aadhaar": r"\b\d{4}\s?\d{4}\s?\d{4}\b",
        "pan": r"\b[A-Z]{5}[0-9]{4}[A-Z]\b",
        "passport": r"\b[A-Z][0-9]{7}\b",
        "credit_card": r"\b(?:\d{4}[-\s]?){3}\d{4}\b",
        "ip_address": r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
        "date_of_birth": r"\b(?:\d{1,2}[-/]\d{1,2}[-/]\d{2,4}|\d{2,4}[-/]\d{1,2}[-/]\d{1,2})\b",
    }

    # Privacy-related keywords
    PRIVACY_KEYWORDS = {
        "en": [
            "personal data", "data collection", "consent", "privacy",
            "data processing", "third party", "data sharing", "cookies",
            "tracking", "profiling", "data retention", "data deletion",
            "data subject", "data controller", "data fiduciary",
            "opt-out", "opt-in", "withdraw consent", "legitimate interest",
            "special categories", "sensitive data", "biometric",
        ],
        "hi": [
            "व्यक्तिगत डेटा", "डेटा संग्रह", "सहमति", "गोपनीयता",
            "डेटा प्रसंस्करण", "तृतीय पक्ष", "डेटा साझाकरण",
            "ट्रैकिंग", "प्रोफाइलिंग", "डेटा प्रतिधारण", "डेटा विलोपन",
            "डेटा विषय", "डेटा नियंत्रक", "डेटा न्यासी",
            "ऑप्ट-आउट", "ऑप्ट-इन", "सहमति वापस",
        ],
    }

    def __init__(self):
        self._nlp_en: Optional[Language] = None
        self._nlp_xx: Optional[Language] = None
        self._load_models()

    def _load_models(self):
        """Load spaCy language models."""
        try:
            self._nlp_en = spacy.load(settings.SPACY_MODEL_EN)
        except OSError:
            print(f"Warning: Could not load {settings.SPACY_MODEL_EN}. NER may not work.")
            self._nlp_en = None

        try:
            # xx_ent_wiki_sm supports multiple languages including Hindi
            self._nlp_xx = spacy.load(settings.SPACY_MODEL_HI)
        except OSError:
            print(f"Warning: Could not load {settings.SPACY_MODEL_HI}. Hindi NER may not work.")
            self._nlp_xx = None

    def detect_language(self, text: str) -> str:
        """
        Detect if text is primarily English or Hindi.

        Returns:
            'en' for English, 'hi' for Hindi, 'mixed' for mixed content
        """
        # Hindi Unicode range: \u0900-\u097F
        hindi_pattern = re.compile(r'[\u0900-\u097F]')
        english_pattern = re.compile(r'[a-zA-Z]')

        hindi_chars = len(hindi_pattern.findall(text))
        english_chars = len(english_pattern.findall(text))

        total = hindi_chars + english_chars

        if total == 0:
            return "en"  # Default to English

        hindi_ratio = hindi_chars / total
        english_ratio = english_chars / total

        if hindi_ratio > 0.7:
            return "hi"
        elif english_ratio > 0.7:
            return "en"
        else:
            return "mixed"

    def analyze(self, text: str) -> AnalysisResult:
        """
        Perform comprehensive text analysis.

        Args:
            text: Text content to analyze

        Returns:
            AnalysisResult with entities, PII, keywords, etc.
        """
        language = self.detect_language(text)

        # Choose appropriate model
        if language == "hi" and self._nlp_xx:
            nlp = self._nlp_xx
        elif self._nlp_en:
            nlp = self._nlp_en
        else:
            nlp = None

        # Basic stats
        sentences = self._count_sentences(text)
        words = len(text.split())

        # NER
        entities = []
        if nlp:
            doc = nlp(text[:100000])  # Limit text size
            entities = [
                EntityResult(
                    text=ent.text,
                    label=ent.label_,
                    start=ent.start_char,
                    end=ent.end_char,
                )
                for ent in doc.ents
            ]

        # PII detection
        pii_detected = self.detect_pii(text)

        # Keyword extraction
        keywords = self.extract_privacy_keywords(text, language)

        return AnalysisResult(
            language=language,
            word_count=words,
            sentence_count=sentences,
            entities=entities,
            pii_detected=pii_detected,
            keywords=keywords,
        )

    def detect_pii(self, text: str) -> List[Dict]:
        """
        Detect PII patterns in text.

        Returns:
            List of detected PII with type and location
        """
        pii_found = []

        for pii_type, pattern in self.PII_PATTERNS.items():
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                pii_found.append({
                    "type": pii_type,
                    "value": match.group()[:4] + "***",  # Mask PII
                    "start": match.start(),
                    "end": match.end(),
                })

        return pii_found

    def extract_privacy_keywords(self, text: str, language: str = "en") -> List[str]:
        """
        Extract privacy-related keywords from text.

        Args:
            text: Text to analyze
            language: Language code ('en', 'hi', or 'mixed')

        Returns:
            List of found privacy keywords
        """
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

    def _count_sentences(self, text: str) -> int:
        """Count sentences in text."""
        # Simple sentence counting based on punctuation
        sentence_endings = re.findall(r'[.!?।]', text)
        return max(len(sentence_endings), 1)

    def extract_data_purposes(self, text: str) -> List[str]:
        """
        Extract stated purposes for data collection.

        Looks for phrases like "we use your data to...", "for the purpose of..."
        """
        purposes = []

        # English purpose patterns
        en_patterns = [
            r"(?:we|our company|the company)\s+(?:use|collect|process).*?(?:to|for)\s+([^.!?]+)",
            r"for\s+the\s+purpose\s+of\s+([^.!?]+)",
            r"in\s+order\s+to\s+([^.!?]+)",
            r"used\s+(?:to|for)\s+([^.!?]+)",
        ]

        for pattern in en_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                purpose = match.group(1).strip()
                if len(purpose) > 10 and len(purpose) < 200:
                    purposes.append(purpose)

        return purposes[:10]  # Limit to top 10

    def check_plain_language(self, text: str) -> Tuple[bool, List[str]]:
        """
        Check if text uses plain, understandable language.

        Returns:
            Tuple of (is_plain_language, issues_found)
        """
        issues = []

        # Check for legal jargon
        jargon_terms = [
            "hereinafter", "whereas", "notwithstanding", "heretofore",
            "aforementioned", "hereunder", "pursuant to", "inter alia",
            "mutatis mutandis", "prima facie",
        ]

        text_lower = text.lower()
        for term in jargon_terms:
            if term in text_lower:
                issues.append(f"Legal jargon detected: '{term}'")

        # Check for overly long sentences
        sentences = re.split(r'[.!?]', text)
        for i, sentence in enumerate(sentences):
            words = len(sentence.split())
            if words > 50:
                issues.append(f"Very long sentence ({words} words) detected")

        is_plain = len(issues) == 0

        return is_plain, issues
