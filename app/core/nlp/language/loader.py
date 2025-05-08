# core/nlp/language/loader.py
import yaml
import logging
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger(__name__)


class IntentLoader:
    def __init__(self, config_path: Path):
        self.config_path = config_path
        self._intents: Dict[str, Any] = {}

    def load_all(self) -> Dict[str, Any]:
        """Load all language configurations from YAML files"""
        for lang in ["en", "ru", "tg"]:
            file_path = self.config_path / f"intents_{lang}.yaml"
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    self._intents[lang] = yaml.safe_load(f)
            except Exception as e:
                logger.error(f"Failed to load intents for {lang}: {str(e)}")
                self._intents[lang] = {}
        return self._intents

    def get_intent(self, lang: str, intent_name: str) -> Dict[str, Any]:
        return self._intents.get(lang, {}).get(intent_name, {})
