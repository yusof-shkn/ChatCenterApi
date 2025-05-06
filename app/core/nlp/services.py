import spacy
from spacy.matcher import Matcher
from pathlib import Path
import yaml
from typing import Dict
from app.core.config import settings
from .schemas import IntentConfig
from .utils import load_yaml_config


class NLPService:
    def __init__(self):
        self.nlp = None
        self.matcher = None
        self.intent_configs: Dict[str, IntentConfig] = {}
        self._initialize_nlp()

    def _initialize_nlp(self):
        """Initialize NLP model and intent patterns"""
        try:
            self.nlp = spacy.load(settings.NLP_MODEL_NAME)
            self.matcher = Matcher(self.nlp.vocab)
            self._load_intent_patterns()
        except Exception as e:
            raise RuntimeError(f"Failed to initialize NLP: {str(e)}")

    def _load_intent_patterns(self):
        """Load intent patterns from config file"""
        config_data = load_yaml_config(
            Path(settings.BASE_DIR) / "config" / "intents.yaml"
        )
        for intent_name, data in config_data.items():
            self.intent_configs[intent_name] = IntentConfig(**data)
            self._add_patterns_to_matcher(intent_name, data["patterns"])

    def _add_patterns_to_matcher(self, intent_name: str, patterns: list):
        """Add patterns to spaCy matcher"""
        processed_patterns = [[{"LOWER": text.lower()}] for text in patterns]
        self.matcher.add(intent_name, processed_patterns)

    def determine_intent(self, text: str) -> str:
        """Determine intent from input text"""
        doc = self.nlp(text)
        matches = self.matcher(doc)
        if not matches:
            return "unclear"

        matched_intents = [
            self.nlp.vocab.strings[match_id] for match_id, _, _ in matches
        ]
        return max(set(matched_intents), key=matched_intents.count)
