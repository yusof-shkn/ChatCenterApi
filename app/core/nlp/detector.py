# app/core/nlp/detector.py
import re
from typing import Literal
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

# Tajik-specific Cyrillic characters not used in Russian
TAJIK_SPECIFIC_CHARS = {"Ғ", "ғ", "Ӯ", "ӯ", "Қ", "қ", "Ҳ", "ҳ", "Ҷ", "ҷ", "Ӣ", "ӣ"}
CYRILLIC_RANGE = re.compile(r"[\u0400-\u04FF]")
LATIN_RANGE = re.compile(r"[a-zA-Z]")


def detect_language(text: str) -> Literal["tg", "ru", "en"]:
    """
    Detects language using a multi-stage approach:
    1. Check for Tajik-specific characters
    2. Analyze character set distribution
    3. Use word pattern matching
    """
    if not text.strip():
        return settings.DEFAULT_LANGUAGE

    text = clean_text(text)

    # Stage 1: Check for Tajik-specific characters
    if has_tajik_specific_chars(text):
        return "tg"

    # Stage 2: Script detection
    script = detect_script(text)

    # Stage 3: Language-specific pattern matching
    if script == "cyrillic":
        return detect_cyrillic_language(text)
    elif script == "latin":
        return detect_latin_language(text)

    return settings.DEFAULT_LANGUAGE


def clean_text(text: str) -> str:
    """Normalize text for language detection"""
    return text.lower().strip()[:500]  # Limit to first 500 characters


def has_tajik_specific_chars(text: str) -> bool:
    """Check for presence of Tajik-specific characters"""
    return any(char in TAJIK_SPECIFIC_CHARS for char in text.lower())


def detect_script(text: str) -> Literal["cyrillic", "latin", "mixed", "unknown"]:
    """Determine dominant script in text"""
    cyrillic_count = len(CYRILLIC_RANGE.findall(text))
    latin_count = len(LATIN_RANGE.findall(text))

    if cyrillic_count == 0 and latin_count == 0:
        return "unknown"
    if cyrillic_count / (cyrillic_count + latin_count) > 0.8:
        return "cyrillic"
    if latin_count / (cyrillic_count + latin_count) > 0.8:
        return "latin"
    return "mixed"


def detect_cyrillic_language(text: str) -> Literal["tg", "ru"]:
    """Differentiate between Tajik and Russian"""
    # Check for Russian-specific stop words
    russian_words = {"но", "или", "если", "чтобы", "когда"}
    tajik_words = {"ва", "ё", "ҳангоми", "то", "ки"}

    # Count characteristic word endings
    ru_endings = sum(1 for _ in re.finditer(r"\b\w+ый\b|\b\w+ая\b|\b\w+ое\b", text))
    tg_endings = sum(1 for _ in re.finditer(r"\b\w+ӣ\b|\b\w+ҳо\b", text))

    # Check for overlapping vocabulary
    ru_score = sum(1 for word in text.split() if word in russian_words)
    tg_score = sum(1 for word in text.split() if word in tajik_words)

    if tg_score > ru_score or tg_endings > ru_endings:
        return "tg"
    return "ru"


def detect_latin_language(text: str) -> Literal["en"]:
    """Confirm English text"""
    # Check for English-specific articles and common words
    english_indicators = {"the", "and", "ing", "to", "of"}
    return "en" if any(word in text for word in english_indicators) else "en"
