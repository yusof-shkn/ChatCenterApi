import logging
import random
from typing import Dict, Tuple, Optional, List

from spacy.matcher import Matcher
from spacy.tokens import Doc
from spacy.util import filter_spans

from app.core.config import settings
from .models import get_nlp_pipeline
from .schemas import IntentConfig
from .detector import detect_language

logger = logging.getLogger(__name__)


class NLPService:
    def __init__(self):
        self._pipelines: Dict[str, Tuple] = {}
        self._lang_map = {
            "en": "english",
            "ru": "russian",
            "tg": "tajiki",
        }
        self._response_lang_map = {
            "english": "en",
            "russian": "ru",
            "tajik": "tg",
        }
        self._city_patterns = [
            [{"LOWER": "in"}, {"ENT_TYPE": {"IN": ["GPE", "LOC"]}, "OP": "+"}],
            [{"LOWER": "at"}, {"ENT_TYPE": {"IN": ["GPE", "LOC"]}, "OP": "+"}],
        ]

    def _get_pipeline(self, lang_key: str):
        if lang_key not in self._pipelines:
            logger.info("Loading NLP pipeline for '%s'", lang_key)
            try:
                nlp, matcher, intent_configs = get_nlp_pipeline(lang_key)
                self._validate_intent_patterns(intent_configs)
                self._pipelines[lang_key] = (nlp, matcher, intent_configs)
                logger.debug(
                    "Loaded pipeline for %s: %d intents", lang_key, len(intent_configs)
                )
            except Exception as e:
                logger.error("Pipeline load failed for %s: %s", lang_key, e)
                raise
        return self._pipelines[lang_key]

    def determine_intent(self, text: str) -> Tuple[str, str, dict, str]:
        lang_code = detect_language(text)
        lang_key = self._lang_map.get(lang_code, settings.DEFAULT_LANGUAGE)
        response_lang = self._response_lang_map.get(lang_key, "en")  # Get 2-letter code

        try:
            nlp, matcher, intent_configs = self._get_pipeline(lang_key)
            doc = nlp(text)
            entities = self._extract_entities(doc)

            matches = matcher(doc)
            if not matches:
                return (
                    "unclear",
                    self._get_fallback_response(response_lang),
                    entities,
                    response_lang,
                )

            best_intent = self._get_best_intent(doc, matches)
            config = intent_configs.get(best_intent)

            # Get localized response
            response = self._get_localized_response(config, response_lang)
            return best_intent, response, entities, response_lang

        except Exception as e:
            logger.error(f"NLP processing failed: {str(e)}")
            return (
                "error",
                self._get_fallback_response(response_lang),
                {},
                response_lang,
            )

    def _get_localized_response(self, config: Optional[IntentConfig], lang: str) -> str:
        """Handle both list and dict response formats"""
        if not config or not config.responses:
            return self._get_fallback_response(lang)

        # Handle dictionary format with language keys
        if isinstance(config.responses, dict):
            localized = config.responses.get(lang, config.responses.get("en", []))
            return (
                random.choice(localized)
                if localized
                else self._get_fallback_response(lang)
            )

        # Handle simple list format
        return random.choice(config.responses)

    def _get_fallback_response(self, lang_code: str) -> str:  # Correct signature
        """Language-specific fallback responses"""
        fallbacks = {
            "ru": [
                "Не могли бы вы переформулировать вопрос?",
                "Я не совсем понимаю. Можете уточнить?",
                "Позвольте мне уточнить...",
            ],
            "tg": [
                "Лутфан такрор кунед?",
                "Ман наметавонам дарк кунам. Шумо шарҳ диҳед?",
                "Ман мехоҳам санҷам...",
            ],
            "en": [
                "Could you please rephrase that?",
                "I'm not sure I understand. Can you clarify?",
                "Let me check that for you...",
            ],
        }
        return random.choice(fallbacks.get(lang_code, fallbacks["en"]))

    def _extract_entities(self, doc: Doc) -> dict:
        """Enhanced entity extraction with multiple strategies"""
        entities = {"city": None, "time": "today"}

        # First pass with named entities
        for ent in doc.ents:
            if ent.label_ in ("GPE", "LOC", "FAC", "ORG"):
                entities["city"] = ent.text
            elif ent.label_ == "DATE":
                entities["time"] = ent.text.lower()

        # Pattern-based city detection with improved matching
        if not entities["city"]:
            matcher = Matcher(doc.vocab)
            patterns = [
                [{"LOWER": "in"}, {"ENT_TYPE": {"IN": ["GPE", "LOC"]}, "OP": "+"}],
                [{"LOWER": "at"}, {"ENT_TYPE": {"IN": ["GPE", "LOC"]}, "OP": "+"}],
                [
                    {"LOWER": "weather"},
                    {"LOWER": "in"},
                    {"ENT_TYPE": {"IN": ["GPE", "LOC"]}},
                ],
            ]
            matcher.add("CITY_CONTEXT", patterns)
            matches = matcher(doc)

            for _, start, end in matches:
                span = doc[start:end]
                if span.ents:
                    cities = [
                        e.text for e in span.ents if e.label_ in ("GPE", "LOC", "FAC")
                    ]
                    if cities:
                        entities["city"] = cities[-1]
                else:
                    # Handle multi-word cities like "New York"
                    city_tokens = [
                        token.text
                        for token in span
                        if token.ent_type_ in ("GPE", "LOC")
                    ]
                    if city_tokens:
                        entities["city"] = " ".join(city_tokens)

        # Time normalization
        entities["time"] = self._normalize_time(entities["time"])
        logger.debug(f"Extracted entities: {entities}")
        return entities

    def _get_best_intent(self, doc: Doc, matches: list) -> str:
        """Determine the most likely intent from matches"""
        seen_spans = []
        intent_counts = {}

        for match_id, start, end in matches:
            span = doc[start:end]
            # Replace spans.overlaps() with custom check
            overlap = False
            for s in seen_spans:
                if span.start < s.end and span.end > s.start:
                    overlap = True
                    break

            if not overlap:
                seen_spans.append(span)
                intent_name = doc.vocab.strings[match_id]
                intent_counts[intent_name] = intent_counts.get(intent_name, 0) + 1

        return max(intent_counts, key=intent_counts.get) if intent_counts else "unclear"

    def _get_response(self, config: Optional[IntentConfig]) -> str:
        """Safely get response from IntentConfig"""
        if not config or not config.responses:
            return self._get_fallback_response()
        return random.choice(config.responses)

    def _normalize_time(self, time_str: str) -> str:
        """Standardize time references"""
        time_str = time_str.lower()
        if any(t in time_str for t in ["tomorrow", "next day"]):
            return "tomorrow"
        if any(t in time_str for t in ["yesterday", "past"]):
            return "yesterday"
        return "today"

    def _validate_intent_patterns(self, intent_configs: Dict[str, IntentConfig]):
        """Validate all patterns are proper spaCy matcher patterns"""
        for intent_name, config in intent_configs.items():
            for pattern in config.patterns:
                if not isinstance(pattern, list) or not all(
                    isinstance(p, dict) for p in pattern
                ):
                    raise ValueError(
                        f"Invalid pattern format for intent '{intent_name}'. "
                        "Expected List[Dict], got {type(pattern)}"
                    )
