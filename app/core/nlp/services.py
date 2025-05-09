import logging
import random
from typing import Dict, Tuple, Any
from dataclasses import dataclass

from spacy.matcher import Matcher
from spacy.tokens import Doc

from app.core.nlp.language.detector import LanguageDetector, ScriptDetector
from app.core.nlp.language.manager import LanguageManager
from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class NLPResult:
    intent: str
    response: str
    entities: Dict[str, Any]
    language: str
    confidence: float


class NLPService:
    def __init__(
        self,
        language_manager: LanguageManager,
        language_detector: LanguageDetector,
        script_detector: ScriptDetector,
    ):
        logger.info("Initializing NLPService")
        self._pipelines: Dict[str, Tuple] = {}
        self.language_manager = language_manager
        self.language_detector = language_detector
        self.script_detector = script_detector
        self._entity_patterns = [
            [{"LOWER": "in"}, {"ENT_TYPE": {"IN": ["GPE", "LOC"]}, "OP": "+"}],
            [{"LOWER": "at"}, {"ENT_TYPE": {"IN": ["GPE", "LOC"]}, "OP": "+"}],
        ]

    def process_text(self, text: str) -> NLPResult:
        logger.info("Processing text: '%s'", text)

        # Detect language
        detected_lang = self.language_detector.detect(text)
        normalized_lang = self.language_manager.normalize_language(detected_lang)

        try:
            # Get the primary pipeline for the detected language
            primary_nlp, primary_matcher, primary_intent_configs = self._get_pipeline(
                normalized_lang
            )
            doc = primary_nlp(text)  # Process text with the primary pipeline
            intent = self._match_intents(doc, primary_matcher)

            # If intent is unclear, use the multi-language pipeline's matcher
            if intent == "unclear":
                logger.info("Primary intent unclear, using multi-language matcher")
                _, multi_matcher, multi_intent_configs = self._get_pipeline("multi")
                intent = self._match_intents(
                    doc, multi_matcher
                )  # Reuse the existing doc
                intent_configs = (
                    multi_intent_configs
                    if intent != "unclear"
                    else primary_intent_configs
                )
            else:
                intent_configs = primary_intent_configs

            # Generate response and extract entities
            response = self._get_response(intent, intent_configs, normalized_lang)
            entities = self._extract_entities(doc)

            return NLPResult(
                intent=intent,
                response=response,
                entities=entities,
                language=normalized_lang,
                confidence=self._calculate_confidence(doc),
            )

        except Exception as e:
            logger.error("NLP processing failed: %s", e)
            return self._handle_error(normalized_lang)

    def _get_pipeline(self, lang_key: str):
        """Load or get cached NLP pipeline"""
        if lang_key not in self._pipelines:
            logger.info("Loading pipeline for '%s'", lang_key)
            try:
                from .models import get_nlp_pipeline

                nlp, matcher, configs = get_nlp_pipeline(lang_key)
                self._validate_patterns(configs)
                self._pipelines[lang_key] = (nlp, matcher, configs)
            except Exception as e:
                logger.error("Pipeline load failed: %s", e)
                raise
        return self._pipelines[lang_key]

    def _match_intents(self, doc: Doc, matcher: Matcher) -> str:
        """Match patterns using both spaCy and custom logic"""
        matches = matcher(doc)
        if not matches:
            return "unclear"

        seen_spans = []
        intent_scores = {}

        for match_id, start, end in matches:
            span = doc[start:end]
            if not any(span.start < s.end and span.end > s.start for s in seen_spans):
                seen_spans.append(span)
                intent_name = doc.vocab.strings[match_id]
                intent_scores[intent_name] = intent_scores.get(intent_name, 0) + 1

        return max(intent_scores, key=intent_scores.get, default="unclear")

    def _extract_entities(self, doc: Doc) -> Dict[str, Any]:
        """Extract entities using combined methods"""
        entities = {"city": None, "time": "today"}

        # SpaCy entities
        for ent in doc.ents:
            if ent.label_ in ("GPE", "LOC", "FAC", "ORG"):
                entities["city"] = ent.text
            elif ent.label_ == "DATE":
                entities["time"] = ent.text.lower()

        # Pattern-based fallback
        if not entities["city"]:
            matcher = Matcher(doc.vocab)
            matcher.add("LOCATION", self._entity_patterns)
            matches = matcher(doc)

            for _, start, end in matches:
                span = doc[start:end]
                if span.ents:
                    cities = [e.text for e in span.ents if e.label_ in ("GPE", "LOC")]
                    entities["city"] = cities[-1] if cities else None

        return self._normalize_entities(entities)

    def _get_response(self, intent: str, configs: Dict[str, Any], lang: str) -> str:
        """Generate localized response using language manager"""
        intent_config = configs.get(intent)
        if intent_config and hasattr(intent_config, "responses"):
            responses = intent_config.responses
        else:
            responses = self.language_manager.get_intent_config(lang, intent)
        if not responses:
            responses = self.language_manager.get_fallback_response(lang, "general")
        return random.choice(responses) if responses else ""

    def _normalize_entities(self, entities: Dict) -> Dict:
        """Normalize entity values to standard format"""
        return {
            "city": entities["city"],
            "time": self._normalize_time(entities["time"]),
        }

    def _normalize_time(self, time_str: str) -> str:
        """Normalize time expressions using language-aware rules"""
        time_str = time_str.lower()
        if any(t in time_str for t in ["tomorrow", "next day"]):
            return "tomorrow"
        if any(t in time_str for t in ["yesterday", "past"]):
            return "yesterday"
        return "today"

    def _calculate_confidence(self, doc: Doc) -> float:
        """Calculate confidence score based on match quality"""
        # Implementation details would go here
        return 0.9  # Placeholder value

    def _validate_patterns(self, configs: Dict[str, Any]):
        """Validate intent patterns structure"""
        for intent, config in configs.items():
            if not hasattr(config, "patterns"):
                raise ValueError(f"IntentConfig for {intent} missing 'patterns'")
            for pattern in config.patterns:
                if not isinstance(pattern, list) or not all(
                    isinstance(p, dict) for p in pattern
                ):
                    raise ValueError(f"Invalid pattern format for {intent}")

    def _handle_error(self, lang: str) -> NLPResult:
        """Generate error response using language manager"""
        return NLPResult(
            intent="error",
            response=self.language_manager.get_fallback_response(lang, "error"),
            entities={},
            language=lang,
            confidence=0.0,
        )
