import logging
import re
from random import choice
from typing import Dict, Any
from dataclasses import dataclass
from app.core.nlp.language.manager import LanguageManager
from app.core.nlp.contexts import SupportContext

logger = logging.getLogger(__name__)


class SupportHandler:
    """Handles support-related intents with multi-turn dialog management"""

    def __init__(self, language_manager: LanguageManager):
        self.lm = language_manager
        logger.info("Initialized SupportHandler with LanguageManager")

    async def handle(self, context: SupportContext) -> Dict[str, Any]:
        """Main entry point for support intent processing"""
        logger.debug(
            "Handling support context: text=%s, language=%s, current_intent=%s",
            context.text,
            context.language,
            context.current_intent,
        )
        try:
            if not self._should_handle(context):
                logger.debug("SupportHandler not handling context")
                return context.result

            result = await self._process_support_flow(context)
            logger.info(
                "Support request processed: intent=%s, response=%s",
                result.get("intent", "unknown"),
                result.get("response", "none"),
            )
            return result

        except Exception as e:
            logger.error("Support handling failed: %s", str(e))
            error_response = self._create_error_response(context)
            logger.info(
                "Returning error response: intent=%s, response=%s",
                error_response.get("intent", "unknown"),
                error_response.get("response", "none"),
            )
            return error_response

    def _should_handle(self, context: SupportContext) -> bool:
        """Determine if support handler should process this request"""
        should_handle = (
            context.current_intent in ["support", "support_followup"]
            or context.prev_intent == "support"
        )
        logger.debug(
            "Checking if should handle: current_intent=%s, prev_intent=%s, should_handle=%s",
            context.current_intent,
            context.prev_intent,
            should_handle,
        )
        return should_handle

    async def _process_support_flow(self, context: SupportContext) -> Dict[str, Any]:
        """Execute multi-step support conversation flow"""
        lang = self.lm.normalize_language(context.language)
        logger.debug("Normalized language: %s", lang)
        config = self.lm.get_intent_config("support", lang)
        logger.debug("Retrieved config for support: %s", config)

        if context.prev_intent != "support" and context.retry_count == 0:
            return self._create_initial_response(context, config)

        category = self._detect_category(context.text, lang)
        return await self._handle_category_flow(context, category, config)

    def _create_initial_response(
        self, context: SupportContext, config: Dict
    ) -> Dict[str, Any]:
        """Handle initial support request"""
        lang = self.lm.normalize_language(context.language)
        responses = config.get("responses")
        if not responses:
            logger.warning(
                "No responses found in config for support, language=%s", lang
            )
            try:
                responses = [self.lm.get_fallback_response(lang, "support")]
            except Exception as e:
                logger.warning(
                    "Failed to get fallback response for 'support': %s", str(e)
                )
                default_responses = {
                    "en": ["How can I assist you with your support query?"],
                    "ru": ["Как я могу помочь с вашим запросом поддержки?"],
                    "tj": [
                        "Чӣ тавр ман метавонам бо дархости дастгирии шумо кумак кунам?"
                    ],
                }
                responses = default_responses.get(lang, default_responses["en"])

        response = choice(responses)
        logger.info("Selected initial response: %s", response)
        return {
            **context.result,
            "intent": "support",
            "response": response,
            "retry_count": context.retry_count + 1,
        }

    async def _handle_category_flow(
        self, context: SupportContext, category: str, config: Dict
    ) -> Dict[str, Any]:
        """Process category-specific follow-up flow"""
        followup_config = config.get("followups", {}).get(
            category, config.get("followups", {}).get("other", {})
        )
        logger.debug(
            "Selected followup config for category=%s: %s", category, followup_config
        )

        if not context.prev_entities.get(f"_support_asked_{category}"):
            return self._create_followup_question(context, category, followup_config)

        return self._create_resolution_response(context, followup_config)

    def _create_followup_question(
        self, context: SupportContext, category: str, config: Dict
    ) -> Dict[str, Any]:
        """Create follow-up question response"""
        lang = self.lm.normalize_language(context.language)
        updated_entities = {**context.entities, f"_support_asked_{category}": True}
        question = config.get("question")
        if not question:
            logger.warning(
                "No question found in config for category=%s, language=%s",
                category,
                lang,
            )
            try:
                question = self.lm.get_fallback_response(lang, "support_prompt")
            except Exception as e:
                logger.warning(
                    "Failed to get fallback response for 'support_prompt': %s", str(e)
                )
                default_questions = {
                    "en": ["Can you provide more details about your issue?"],
                    "ru": [
                        "Можете ли вы предоставить больше деталей о вашей проблеме?"
                    ],
                    "tj": [
                        "Оё шумо метавонед тафсилоти бештар дар бораи мушкили худ пешниҳод кунед?"
                    ],
                }
                question = default_questions.get(lang, default_questions["en"])[0]

        logger.info("Selected followup question: %s", question)
        return {
            **context.result,
            "intent": "support_followup",
            "response": question,
            "entities": updated_entities,
        }

    def _create_resolution_response(
        self, context: SupportContext, config: Dict
    ) -> Dict[str, Any]:
        """Create final resolution response"""
        lang = self.lm.normalize_language(context.language)
        responses = config.get("responses")
        if not responses:
            logger.warning(
                "No responses found in config for resolution, language=%s", lang
            )
            try:
                responses = [self.lm.get_fallback_response(lang, "support_resolution")]
            except Exception as e:
                logger.warning(
                    "Failed to get fallback response for 'support_resolution': %s",
                    str(e),
                )
                default_responses = {
                    "en": ["I hope that helps. Let me know if you need anything else."],
                    "ru": ["Надеюсь, это помогло. Дайте знать, если нужно что-то еще."],
                    "tj": [
                        "Умедворам, ки ин кумак кард. Агар чизи дигаре лозим бошад, маро огоҳ кунед."
                    ],
                }
                responses = default_responses.get(lang, default_responses["en"])

        response = choice(responses)
        logger.info("Selected resolution response: %s", response)
        return {
            **context.result,
            "intent": "support_resolution",
            "response": response,
        }

    def _detect_category(self, text: str, lang: str) -> str:
        """Detect support category using language-specific keywords"""
        config = self.lm.get_intent_config("support", lang)
        text_lower = text.lower()

        for category, cfg in config.get("followups", {}).items():
            if any(
                re.search(rf"\b{re.escape(kw)}\b", text_lower)
                for kw in cfg.get("keywords", [])
            ):
                logger.info("Detected support category: %s", category)
                return category
        logger.info("Detected support category: other")
        return "other"

    def _create_error_response(self, context: SupportContext) -> Dict[str, Any]:
        """Create error response for support flow"""
        lang = self.lm.normalize_language(context.language)
        try:
            error_msg = self.lm.get_fallback_response(lang, "error")
        except Exception as e:
            logger.warning("Failed to get fallback error response: %s", str(e))
            default_error_msgs = {
                "en": ["Sorry, something went wrong. Please try again later."],
                "ru": ["Извините, что-то пошло не так. Пожалуйста, попробуйте позже."],
                "tj": ["Бубахшед, чизе хато шуд. Лутфан, баъдтар кӯшиш кунед."],
            }
            error_msg = default_error_msgs.get(lang, default_error_msgs["en"])[0]

        logger.info("Selected error response: %s", error_msg)
        return {**context.result, "intent": "support_error", "response": error_msg}
