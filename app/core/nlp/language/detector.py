# core/nlp/language/detector.py
import re
from typing import Literal
from .config import DetectionConfig


class ScriptDetector:
    CYRILLIC = re.compile(r"[\u0400-\u04FF]")
    LATIN = re.compile(r"[a-zA-Z]")

    def __init__(self, config: DetectionConfig):
        self.config = config

    def detect_script(
        self, text: str
    ) -> Literal["cyrillic", "latin", "mixed", "unknown"]:
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

    def detect(self, text: str) -> Literal["tg", "ru", "en"]:
        text = self._clean_text(text)

        if self._has_tajik_chars(text):
            return "tg"

        script = self.script_detector.detect_script(text)

        if script == "cyrillic":
            return self._detect_cyrillic_lang(text)
        if script == "latin":
            return "en"
        return "en"

    def _clean_text(self, text: str) -> str:
        return text.lower().strip()[: self.config.max_input_length]

    def _has_tajik_chars(self, text: str) -> bool:
        return any(c in text.lower() for c in self.config.tajik_chars)

    def _detect_cyrillic_lang(self, text: str) -> Literal["tg", "ru"]:
        ru_score = sum(1 for w in text.split() if w in self.config.russian_words)
        tg_score = sum(1 for w in text.split() if w in self.config.tajik_words)
        return "tg" if tg_score > ru_score else "ru"
