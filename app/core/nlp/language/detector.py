# core/nlp/language/detector.py
import re
from typing import Literal
from .config import DetectionConfig


class ScriptDetector:
    CYRILLIC = re.compile(r"[\u0400-\u04FF\u0500-\u052F]")  # Expanded Cyrillic range
    LATIN = re.compile(r"[a-zA-Z]")
    TAJIK_SPECIFIC = re.compile(
        r"[\u04B3\u04B7\u04B9\u04AF\u04E3\u04BB\u049B\u0493\u04A3\u04A1]"
    )  # Tajik-specific chars

    def __init__(self, config: DetectionConfig):
        self.config = config

    def detect_script(
        self, text: str
    ) -> Literal["cyrillic", "latin", "mixed", "unknown"]:
        # First check for Tajik-specific characters
        if self.TAJIK_SPECIFIC.search(text):
            return "cyrillic"  # Force Cyrillic detection for Tajik

        cyrillic = len(self.CYRILLIC.findall(text))
        latin = len(self.LATIN.findall(text))

        if cyrillic + latin == 0:
            return "unknown"
        if cyrillic / (cyrillic + latin) > self.config.script_threshold:
            return "cyrillic"
        if latin / (cyrillic + latin) > self.config.script_threshold:
            return "latin"
        return "mixed"


class LanguageDetector:
    def __init__(self, config: DetectionConfig, script_detector: ScriptDetector):
        self.config = config
        self.script_detector = script_detector
        self.tajik_indicators = {
            "ҳ",
            "ҷ",
            "қ",
            "ғ",
            "ӣ",
            "ӯ",
            "є",
            "ї",
            "і",
            "ў",  # Tajik-specific Cyrillic
        }
        self.common_tajik_words = {
            # Greetings
            "салом",
            "ассалом",
            "субҳ",
            "рӯз",
            "шом",
            "хайрбахшт",
            "чӣ",
            "хел",
            "субҳба",
            "рӯзба",
            "хамин",
            # Farewells
            "хайр",
            "худоҳофиз",
            "то",
            "дидор",
            "баъд",
            "паёмд",
            "баъдан",
            "шукр",
            "хайрамидидор",
            # Company / business
            "ширкат",
            "хизматрасонӣ",
            "хизмат",
            "дафтари",
            "маҳсулот",
            "хидмат",
            "инноватсионӣ",
            "технологӣ",
            "корманд",
            "раҳбар",
            "оянда",
            "мақсад",
            "визиён",
            "истеъмолкунанда",
            # Help / support
            "кумак",
            "йорӣ",
            "дастгирӣ",
            "маслиҳат",
            "мушкил",
            "қарар",
            "ҳал",
            "роҳнамоӣ",
            "тамос",
            "талош",
            "барқарор",
            "истгоҳ",
            # Weather
            "обуҳаво",
            "ҳарорат",
            "борон",
            "боронӣ",
            "барф",
            "шамол",
            "намӣ",
            "гармӣ",
            "сардӣ",
            "табъи",
            "тишно",
            "пешгӯӣ",
            "об",
            "ҳаво",
            "табасум",
            "тоза",
        }

    def _clean_text(self, text: str) -> str:
        """Clean and normalize input text for processing"""
        return text.lower().strip()[: self.config.max_input_length]

    def detect(self, text: str) -> Literal["tg", "ru", "en"]:
        text = self._clean_text(text)

        # First check for explicit Tajik markers
        if self._is_definitely_tajik(text):
            return "tg"

        script = self.script_detector.detect_script(text)

        if script == "cyrillic":
            return self._enhanced_cyrillic_detection(text)
        if script == "latin":
            return "en"
        return "en"

    def _is_definitely_tajik(self, text: str) -> bool:
        # Check for Tajik-specific characters
        if any(c in self.tajik_indicators for c in text.lower()):
            return True

        # Check for common Tajik words/phrases
        clean_text = text.lower()
        return any(word in clean_text for word in self.common_tajik_words)

    def _enhanced_cyrillic_detection(self, text: str) -> Literal["tg", "ru"]:
        # Score based on multiple factors
        tajik_score = 0
        russian_score = 0

        # 1. Character-based scoring
        tajik_score += sum(1 for c in text if c in self.tajik_indicators)

        # 2. Word list matching
        words = text.lower().split()
        tajik_score += sum(1 for w in words if w in self.common_tajik_words)
        russian_score += sum(1 for w in words if w in self.config.russian_words)

        # 3. N-gram analysis for common Tajik patterns
        for i in range(len(text) - 1):
            bigram = text[i : i + 2].lower()
            if bigram in {"ҳо", "ҷа", "қа", "ға"}:
                tajik_score += 2

        # 4. Length-based detection for short texts
        if len(words) < 3:
            if any(w in self.common_tajik_words for w in words):
                return "tg"
            if any(w in self.config.russian_words for w in words):
                return "ru"

        # Weighted decision making
        tajik_score *= self.config.tajik_weight
        russian_score *= self.config.russian_weight

        return "tg" if tajik_score > russian_score else "ru"
