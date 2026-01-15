"""
DPDP GUI Compliance Scanner - Readability Analyzer

Calculates readability scores for privacy notices.
"""
import math
import re
from dataclasses import dataclass
from typing import Dict, List, Tuple

from app.core.config import settings


@dataclass
class ReadabilityScore:
    """Readability analysis result."""
    flesch_reading_ease: float
    flesch_kincaid_grade: float
    gunning_fog_index: float
    smog_index: float
    average_score: float
    grade_level: str
    is_compliant: bool
    recommendations: List[str]


class ReadabilityAnalyzer:
    """
    Analyzer for text readability.

    Implements multiple readability formulas:
    - Flesch Reading Ease
    - Flesch-Kincaid Grade Level
    - Gunning Fog Index
    - SMOG Index

    DPDP requires privacy notices to be in clear, plain language.
    Target: 8th grade reading level or below.
    """

    # Common syllable patterns
    VOWELS = "aeiouy"

    # Words that appear complex but are commonly understood
    FAMILIAR_COMPLEX_WORDS = {
        "privacy", "consent", "information", "collection", "processing",
        "website", "internet", "computer", "electronic", "personal",
        "agreement", "application", "notification", "registration",
    }

    def analyze(self, text: str) -> ReadabilityScore:
        """
        Analyze text readability.

        Args:
            text: Text content to analyze

        Returns:
            ReadabilityScore with multiple metrics
        """
        # Preprocess text
        clean_text = self._preprocess(text)

        # Count basic elements
        word_count = self._count_words(clean_text)
        sentence_count = self._count_sentences(clean_text)
        syllable_count = self._count_syllables(clean_text)
        complex_word_count = self._count_complex_words(clean_text)

        # Avoid division by zero
        if word_count == 0 or sentence_count == 0:
            return ReadabilityScore(
                flesch_reading_ease=0,
                flesch_kincaid_grade=0,
                gunning_fog_index=0,
                smog_index=0,
                average_score=0,
                grade_level="Unable to calculate",
                is_compliant=False,
                recommendations=["Text is too short to analyze"],
            )

        # Calculate scores
        fre = self._flesch_reading_ease(word_count, sentence_count, syllable_count)
        fkg = self._flesch_kincaid_grade(word_count, sentence_count, syllable_count)
        gfi = self._gunning_fog_index(word_count, sentence_count, complex_word_count)
        smog = self._smog_index(sentence_count, complex_word_count)

        # Average grade level (excluding FRE which is a score, not grade)
        avg_grade = (fkg + gfi + smog) / 3

        # Determine grade level description
        grade_level = self._grade_to_description(avg_grade)

        # Check compliance (target: 8th grade or below, FRE >= 60)
        is_compliant = avg_grade <= 8 and fre >= settings.MIN_READABILITY_SCORE

        # Generate recommendations
        recommendations = self._generate_recommendations(
            fre, avg_grade, word_count, sentence_count, complex_word_count
        )

        return ReadabilityScore(
            flesch_reading_ease=round(fre, 1),
            flesch_kincaid_grade=round(fkg, 1),
            gunning_fog_index=round(gfi, 1),
            smog_index=round(smog, 1),
            average_score=round(avg_grade, 1),
            grade_level=grade_level,
            is_compliant=is_compliant,
            recommendations=recommendations,
        )

    def _preprocess(self, text: str) -> str:
        """Clean text for analysis."""
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove special characters but keep punctuation
        text = re.sub(r'[^\w\s.!?]', '', text)
        return text.strip()

    def _count_words(self, text: str) -> int:
        """Count words in text."""
        words = text.split()
        return len(words)

    def _count_sentences(self, text: str) -> int:
        """Count sentences in text."""
        sentences = re.split(r'[.!?]+', text)
        sentences = [s for s in sentences if s.strip()]
        return max(len(sentences), 1)

    def _count_syllables(self, text: str) -> int:
        """Count total syllables in text."""
        words = text.lower().split()
        total = sum(self._syllables_in_word(word) for word in words)
        return max(total, 1)

    def _syllables_in_word(self, word: str) -> int:
        """Count syllables in a single word."""
        word = word.lower().strip(".,!?;:'\"")

        if len(word) <= 3:
            return 1

        # Count vowel groups
        syllables = 0
        prev_vowel = False

        for char in word:
            is_vowel = char in self.VOWELS
            if is_vowel and not prev_vowel:
                syllables += 1
            prev_vowel = is_vowel

        # Adjust for common patterns
        if word.endswith('e'):
            syllables -= 1
        if word.endswith('le') and len(word) > 2 and word[-3] not in self.VOWELS:
            syllables += 1
        if syllables == 0:
            syllables = 1

        return syllables

    def _count_complex_words(self, text: str) -> int:
        """
        Count complex words (3+ syllables).

        Excludes common compound words and proper nouns.
        """
        words = text.lower().split()
        complex_count = 0

        for word in words:
            word = word.strip(".,!?;:'\"")

            # Skip if it's a familiar term
            if word in self.FAMILIAR_COMPLEX_WORDS:
                continue

            # Skip capitalized words (likely proper nouns)
            if word and word[0].isupper():
                continue

            if self._syllables_in_word(word) >= 3:
                complex_count += 1

        return complex_count

    def _flesch_reading_ease(
        self,
        word_count: int,
        sentence_count: int,
        syllable_count: int,
    ) -> float:
        """
        Calculate Flesch Reading Ease score.

        Score interpretation:
        - 90-100: Very easy (5th grade)
        - 80-90: Easy (6th grade)
        - 70-80: Fairly easy (7th grade)
        - 60-70: Standard (8th-9th grade)
        - 50-60: Fairly difficult (10th-12th grade)
        - 30-50: Difficult (college)
        - 0-30: Very difficult (professional)
        """
        asl = word_count / sentence_count  # Average sentence length
        asw = syllable_count / word_count  # Average syllables per word

        score = 206.835 - (1.015 * asl) - (84.6 * asw)

        return max(0, min(100, score))

    def _flesch_kincaid_grade(
        self,
        word_count: int,
        sentence_count: int,
        syllable_count: int,
    ) -> float:
        """Calculate Flesch-Kincaid Grade Level."""
        asl = word_count / sentence_count
        asw = syllable_count / word_count

        grade = (0.39 * asl) + (11.8 * asw) - 15.59

        return max(0, grade)

    def _gunning_fog_index(
        self,
        word_count: int,
        sentence_count: int,
        complex_word_count: int,
    ) -> float:
        """Calculate Gunning Fog Index."""
        asl = word_count / sentence_count
        pcw = (complex_word_count / word_count) * 100  # Percent complex words

        index = 0.4 * (asl + pcw)

        return max(0, index)

    def _smog_index(self, sentence_count: int, complex_word_count: int) -> float:
        """Calculate SMOG Index."""
        if sentence_count < 30:
            # Adjust for shorter texts
            polysyllables = complex_word_count * (30 / sentence_count)
        else:
            polysyllables = complex_word_count

        index = 1.0430 * math.sqrt(polysyllables) + 3.1291

        return max(0, index)

    def _grade_to_description(self, grade: float) -> str:
        """Convert grade level to description."""
        if grade <= 5:
            return "Very Easy (5th grade or below)"
        elif grade <= 6:
            return "Easy (6th grade)"
        elif grade <= 7:
            return "Fairly Easy (7th grade)"
        elif grade <= 8:
            return "Standard (8th grade)"
        elif grade <= 9:
            return "Fairly Difficult (9th grade)"
        elif grade <= 12:
            return "Difficult (High School)"
        else:
            return "Very Difficult (College level or above)"

    def _generate_recommendations(
        self,
        fre: float,
        avg_grade: float,
        word_count: int,
        sentence_count: int,
        complex_word_count: int,
    ) -> List[str]:
        """Generate recommendations for improving readability."""
        recommendations = []

        # Check overall score
        if avg_grade > 8:
            recommendations.append(
                f"Reading level ({avg_grade:.1f}) is above 8th grade. "
                "Simplify language to make it accessible to more users."
            )

        # Check Flesch score
        if fre < settings.MIN_READABILITY_SCORE:
            recommendations.append(
                f"Flesch Reading Ease score ({fre:.1f}) is below {settings.MIN_READABILITY_SCORE}. "
                "Use shorter sentences and simpler words."
            )

        # Check sentence length
        avg_sentence_length = word_count / sentence_count
        if avg_sentence_length > 20:
            recommendations.append(
                f"Average sentence length ({avg_sentence_length:.1f} words) is too long. "
                "Break long sentences into shorter ones."
            )

        # Check complex word usage
        complex_percentage = (complex_word_count / word_count) * 100 if word_count > 0 else 0
        if complex_percentage > 15:
            recommendations.append(
                f"Too many complex words ({complex_percentage:.1f}%). "
                "Replace complex terms with simpler alternatives."
            )

        if not recommendations:
            recommendations.append("Text readability is within acceptable limits.")

        return recommendations

    def compare_texts(self, text1: str, text2: str) -> Dict:
        """Compare readability of two texts."""
        result1 = self.analyze(text1)
        result2 = self.analyze(text2)

        return {
            "text1": {
                "flesch_reading_ease": result1.flesch_reading_ease,
                "average_grade": result1.average_score,
                "is_compliant": result1.is_compliant,
            },
            "text2": {
                "flesch_reading_ease": result2.flesch_reading_ease,
                "average_grade": result2.average_score,
                "is_compliant": result2.is_compliant,
            },
            "better_text": "text1" if result1.flesch_reading_ease > result2.flesch_reading_ease else "text2",
        }
