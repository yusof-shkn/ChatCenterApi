import logging
import re
from random import choice
from typing import Dict, Any

logger = logging.getLogger(__name__)


# SupportHandler
class SupportHandler:
    """
    Handles 'support' and 'help' related intents with multi-turn follow-up logic,
    supporting multiple languages.
    """

    def __init__(self, intent_configs: Dict[str, Dict[str, Any]]):
        logger.info("Initializing SupportHandler")
        self.configs = intent_configs  # e.g., {"en": {...}, "ru": {...}, "tg": {...}}
        logger.debug(
            "Loaded intent configs for languages: %s", list(self.configs.keys())
        )

    async def handle(
        self,
        language: str,
        text: str,
        current_intent: str,
        entities: Dict[str, Any],
        prev_intent: str,
        prev_entities: Dict[str, Any],
        retry_count: int,
        result: Dict[str, Any],
    ) -> Dict[str, Any]:
        logger.info(
            "Handling support intent for language '%s', text: '%s'", language, text
        )
        logger.debug(
            "Input: intent='%s', entities=%s, prev_intent='%s', prev_entities=%s, retry_count=%d",
            current_intent,
            entities,
            prev_intent,
            prev_entities,
            retry_count,
        )

        if current_intent != "support":
            logger.debug("Not a support intent, returning original result")
            return result

        config = self.configs.get(language, self.configs.get("en", {}))
        if not config:
            logger.warning(
                "No config found for language '%s', falling back to 'en'", language
            )
        logger.debug("Using config for language '%s'", language)

        base_responses = config.get("responses", [])
        if not base_responses:
            logger.warning("No base responses found for language '%s'", language)

        if prev_intent != "support" and retry_count == 0:
            response = (
                choice(base_responses)
                if base_responses
                else "Please describe your issue."
            )
            logger.debug("Initial support response: '%s'", response)
            return {
                **result,
                "intent": "support",
                "response": response,
                "retry_count": 1,
            }

        category = self._detect_category(language, text)
        logger.debug("Detected category: '%s'", category)
        cat_cfg = config.get("followups", {}).get(
            category, config.get("followups", {}).get("other", {})
        )
        logger.debug("Category config: %s", cat_cfg)

        asked_key = f"_support_asked_{category}"
        if not prev_entities.get(asked_key):
            updated_entities = {**entities, asked_key: True}
            response = cat_cfg.get("question", "Can you give me more details?")
            logger.debug(
                "Follow-up question: '%s', updated entities: %s",
                response,
                updated_entities,
            )
            return {
                **result,
                "intent": "support_followup",
                "response": response,
                "entities": updated_entities,
            }

        response = choice(cat_cfg.get("responses", ["Let me know if that helps."]))
        logger.debug("Resolution response: '%s'", response)
        result = {
            **result,
            "intent": "support_resolution",
            "response": response,
        }
        logger.debug("Returning result: %s", result)
        return result

    def _detect_category(self, language: str, text: str) -> str:
        """Detects support category based on keywords in the specified language"""
        logger.debug(
            "Detecting support category for language '%s', text: '%s'", language, text
        )
        config = self.configs.get(language, self.configs.get("en", {}))
        text_lower = text.lower()
        for category, cfg in config.get("followups", {}).items():
            for kw in cfg.get("keywords", []):
                if re.search(rf"\b{re.escape(kw)}\b", text_lower):
                    logger.debug("Matched keyword '%s' for category '%s'", kw, category)
                    return category
        logger.debug("No category matched, returning 'other'")
        return "other"
