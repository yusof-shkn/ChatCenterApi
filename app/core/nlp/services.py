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
        logger.info("Initializing NLPService")
        self._pipelines: Dict[str, Tuple] = {}
        self._lang_map = {
            "en": "english",
            "ru": "russian",
            "tg": "tajiki",
        }
        self._response_lang_map = {
            "english": "en",
            "russian": "ru",
            "tajiki": "tg",
        }
        self._city_patterns = [
            [{"LOWER": "in"}, {"ENT_TYPE": {"IN": ["GPE", "LOC"]}, "OP": "+"}],
            [{"LOWER": "at"}, {"ENT_TYPE": {"IN": ["GPE", "LOC"]}, "OP": "+"}],
        ]
        logger.debug(
            "Language maps initialized: lang_map=%s, response_lang_map=%s",
            self._lang_map,
            self._response_lang_map,
        )

    def _get_pipeline(self, lang_key: str):
        logger.debug("Checking pipeline for language '%s'", lang_key)
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
        else:
            logger.debug("Using cached pipeline for %s", lang_key)
        return self._pipelines[lang_key]

    def determine_intent(self, text: str) -> Tuple[str, str, dict, str]:
        logger.info("Processing intent for text: '%s'", text)
        lang_code = detect_language(text)
        logger.debug("Detected language code: '%s'", lang_code)
        lang_key = self._lang_map.get(lang_code, settings.DEFAULT_LANGUAGE)
        logger.debug("Mapped to language key: '%s'", lang_key)
        response_lang = self._response_lang_map.get(lang_key, "en")
        logger.debug("Response language: '%s'", response_lang)

        try:
            nlp, matcher, intent_configs = self._get_pipeline(lang_key)
            logger.debug("Processing text with spaCy pipeline for '%s'", lang_key)
            doc = nlp(text)
            entities = self._extract_entities(doc)

            matches = matcher(doc)
            logger.debug("Found %d intent matches", len(matches))
            if not matches:
                logger.warning("No intent matches for text '%s'", text)
                return (
                    "unclear",
                    self._get_fallback_response(response_lang),
                    entities,
                    response_lang,
                )

            best_intent = self._get_best_intent(doc, matches)
            logger.debug("Selected best intent: '%s'", best_intent)
            config = intent_configs.get(best_intent)
            if not config:
                logger.warning("No config found for intent '%s'", best_intent)
                return (
                    best_intent,
                    self._get_fallback_response(response_lang),
                    entities,
                    response_lang,
                )

            response = self._get_localized_response(config, response_lang)
            logger.debug("Generated response: '%s'", response)
            return best_intent, response, entities, response_lang

        except Exception as e:
            logger.error("NLP processing failed for text '%s': %s", text, e)
            return (
                "error",
                self._get_fallback_response(response_lang),
                {},
                response_lang,
            )

    def _get_localized_response(self, config: Optional[IntentConfig], lang: str) -> str:
        logger.debug("Getting localized response for lang '%s'", lang)
        if not config or not config.responses:
            logger.warning("No valid config or responses for lang '%s'", lang)
            return self._get_fallback_response(lang)

        if isinstance(config.responses, dict):
            logger.debug("Responses are in dict format for lang '%s'", lang)
            localized = config.responses.get(lang, config.responses.get("en", []))
            if not localized:
                logger.warning(
                    "No localized responses for lang '%s', falling back", lang
                )
                return self._get_fallback_response(lang)
            response = random.choice(localized)
            logger.debug("Selected localized response: '%s'", response)
            return response

        logger.debug("Responses are in list format for lang '%s'", lang)
        response = random.choice(config.responses)
        logger.debug("Selected response: '%s'", response)
        return response

    def _get_fallback_response(self, lang_code: str) -> str:
        logger.debug("Generating fallback response for lang '%s'", lang_code)
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
        response = random.choice(fallbacks.get(lang_code, fallbacks["en"]))
        logger.debug("Selected fallback response: '%s'", response)
        return response

    def _extract_entities(self, doc: Doc) -> dict:
        logger.debug("Extracting entities from doc")
        entities = {"city": None, "time": "today"}

        for ent in doc.ents:
            if ent.label_ in ("GPE", "LOC", "FAC", "ORG"):
                entities["city"] = ent.text
                logger.debug("Found city entity: '%s'", ent.text)
            elif ent.label_ == "DATE":
                entities["time"] = ent.text.lower()
                logger.debug("Found time entity: '%s'", ent.text)

        if not entities["city"]:
            logger.debug("No city entity found, applying pattern-based detection")
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
                        logger.debug("Pattern-based city found: '%s'", entities["city"])
                else:
                    city_tokens = [
                        token.text
                        for token in span
                        if token.ent_type_ in ("GPE", "LOC")
                    ]
                    if city_tokens:
                        entities["city"] = " ".join(city_tokens)
                        logger.debug("Multi-word city found: '%s'", entities["city"])

        entities["time"] = self._normalize_time(entities["time"])
        logger.debug("Final extracted entities: %s", entities)
        return entities

    def _get_best_intent(self, doc: Doc, matches: list) -> str:
        logger.debug("Determining best intent from %d matches", len(matches))
        seen_spans = []
        intent_counts = {}

        for match_id, start, end in matches:
            span = doc[start:end]
            overlap = False
            for s in seen_spans:
                if span.start < s.end and span.end > s.start:
                    overlap = True
                    break

            if not overlap:
                seen_spans.append(span)
                intent_name = doc.vocab.strings[match_id]
                intent_counts[intent_name] = intent_counts.get(intent_name, 0) + 1
                logger.debug(
                    "Counted intent '%s' for span '%s'", intent_name, span.text
                )

        if not intent_counts:
            logger.warning("No valid intents found")
            return "unclear"

        best_intent = max(intent_counts, key=intent_counts.get)
        logger.debug(
            "Selected best intent: '%s' with %d occurrences",
            best_intent,
            intent_counts[best_intent],
        )
        return best_intent

    def _get_response(self, config: Optional[IntentConfig]) -> str:
        logger.debug("Getting response from config")
        if not config or not config.responses:
            logger.warning("No valid config or responses, using fallback")
            return self._get_fallback_response("en")
        response = random.choice(config.responses)
        logger.debug("Selected response: '%s'", response)
        return response

    def _normalize_time(self, time_str: str) -> str:
        logger.debug("Normalizing time: '%s'", time_str)
        time_str = time_str.lower()
        if any(t in time_str for t in ["tomorrow", "next day"]):
            logger.debug("Normalized to 'tomorrow'")
            return "tomorrow"
        if any(t in time_str for t in ["yesterday", "past"]):
            logger.debug("Normalized to 'yesterday'")
            return "yesterday"
        logger.debug("Normalized to 'today'")
        return "today"

    def _validate_intent_patterns(self, intent_configs: Dict[str, IntentConfig]):
        logger.debug("Validating intent patterns")
        for intent_name, config in intent_configs.items():
            logger.debug("Checking patterns for intent '%s'", intent_name)
            for pattern in config.patterns:
                if not isinstance(pattern, list) or not all(
                    isinstance(p, dict) for p in pattern
                ):
                    logger.error(
                        "Invalid pattern format for intent '%s': %s",
                        intent_name,
                        pattern,
                    )
                    raise ValueError(
                        f"Invalid pattern format for intent '{intent_name}'. "
                        f"Expected List[Dict], got {type(pattern)}"
                    )
        logger.debug("All intent patterns validated successfully")
