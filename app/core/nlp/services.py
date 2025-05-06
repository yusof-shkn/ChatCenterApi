# app/api/v1/nlp/services.py

import logging
import random
from typing import Dict, Tuple

from app.core.config import settings
from .models import get_nlp_pipeline
from .detector import detect_language

logger = logging.getLogger(__name__)


class NLPService:
    def __init__(self):
        # Cache loaded pipelines by lang key
        self._pipelines: Dict[str, Tuple] = {}

        # map langdetect codes → our registry keys
        self._lang_map = {
            "en": "english",
            "ru": "russian",
            "tg": "tajiki",
        }

    def _get_pipeline(self, lang_key: str):
        if lang_key not in self._pipelines:
            logger.debug("Loading NLP pipeline for language '%s'", lang_key)
            try:
                self._pipelines[lang_key] = get_nlp_pipeline(lang_key)
                logger.info("Loaded pipeline for '%s'", lang_key)
            except Exception as e:
                logger.error(
                    "Failed to load pipeline for '%s': %s", lang_key, e, exc_info=True
                )
                raise
        return self._pipelines[lang_key]

    def determine_intent(self, text: str) -> Tuple[str, str]:
        # 1) detect the incoming language
        code = detect_language(text)
        lang_key = self._lang_map.get(code, settings.DEFAULT_LANGUAGE)
        logger.debug(
            "Detected language code '%s' → using pipeline '%s'", code, lang_key
        )

        # 2) load or retrieve the pipeline
        nlp, matcher, intent_configs = self._get_pipeline(lang_key)

        # 3) run the matcher
        logger.debug("Processing text through spaCy: %r", text)
        doc = nlp(text)
        matches = matcher(doc)
        logger.debug("Found %d matches", len(matches))

        if not matches:
            logger.warning("No intent matched for text: %r", text)
            return "unclear", "I'm not sure how to respond to that."

        # collect all matched intent names
        intents = [nlp.vocab.strings[match_id] for match_id, _, _ in matches]
        best_intent = max(set(intents), key=intents.count)
        logger.info("Determined intent '%s' for text: %r", best_intent, text)

        # 4) pick a response at random (or first)
        config = intent_configs.get(best_intent)
        if not config or not config.responses:
            logger.error("No response templates found for intent '%s'", best_intent)
            return best_intent, "…"

        response = random.choice(config.responses)
        logger.debug("Selected response for intent '%s': %r", best_intent, response)
        return best_intent, response
