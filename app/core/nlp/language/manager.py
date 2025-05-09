# core/nlp/language/manager.py
from typing import Dict, Any
from .config import LanguageConfig
from .loader import IntentLoader


class LanguageManager:
    def __init__(self, config: LanguageConfig, loader: IntentLoader):
        self.config = config
        self.loader = loader
        self._intents = loader.load_all()

    def normalize_language(self, lang_input: str) -> str:
        return self.config.aliases.get(lang_input.lower(), self.config.code)

    def get_intent_config(self, intent_name: str, lang: str) -> Dict[str, Any]:
        normalized = self.normalize_language(lang)
        return self.loader.get_intent(normalized, intent_name)

    def get_fallback_response(self, lang: str, response_type: str) -> str:
        normalized = self.normalize_language(lang)
        return self.config.fallbacks.get(normalized, {}).get(
            response_type, self.config.fallbacks[self.config.code][response_type]
        )
    # Add to LanguageManager
    def normalize_tajiki(text: str) -> str:
        """Normalize Tajik text variations"""
        return text.replace("ӯ", "ў").replace("ҳ", "х")  # Example normalizations