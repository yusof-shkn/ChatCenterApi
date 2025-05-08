import re
from random import choice
from typing import Dict, Any
from datetime import datetime
import pytz
import logging
from app.core.nlp.language.manager import LanguageManager
from dataclasses import dataclass
from app.core.nlp.contexts import SocialContext

logger = logging.getLogger(__name__)


class SocialHandler:
    """Handles social interactions like greetings and farewells"""

    EMOJI_MAP = {
        "greeting": ["👋", "😊", "🌞", "🖐️"],
        "farewell": ["👋", "👍", "😊", "✨"],
    }

    def __init__(self, language_manager: LanguageManager):
        self.lm = language_manager
        logger.info("Initialized SocialHandler with LanguageManager")

    async def handle(self, context: SocialContext) -> Dict[str, Any]:
        """Process social interactions"""
        logger.debug(
            "Handling social context: text=%s, language=%s, current_intent=%s",
            context.text,
            context.language,
            context.current_intent,
        )
        try:
            if not self._is_social_intent(context.current_intent):
                logger.debug("SocialHandler not handling context")
                return context.result

            result = await self._handle_social_response(context)
            logger.info(
                "Social request processed: intent=%s, response=%s",
                result.get("intent", "unknown"),
                result.get("response", "none"),
            )
            return result

        except Exception as e:
            logger.error("Social handling failed: %s", str(e))
            error_response = self._create_error_response(context)
            logger.info(
                "Returning error response: intent=%s, response=%s",
                error_response.get("intent", "unknown"),
                error_response.get("response", "none"),
            )
            return error_response

    def _is_social_intent(self, intent: str) -> bool:
        """Check if intent is social type"""
        is_social = intent in ["greeting", "farewell"]
        logger.debug(
            "Checking social intent: intent=%s, is_social=%s", intent, is_social
        )
        return is_social

    async def _handle_social_response(self, context: SocialContext) -> Dict[str, Any]:
        """Generate appropriate social response"""
        lang = self.lm.normalize_language(context.language)
        logger.debug("Normalized language: %s", lang)
        config = self.lm.get_intent_config(context.current_intent, lang)
        logger.debug(
            "Retrieved config for intent=%s: %s", context.current_intent, config
        )

        if not config:
            logger.warning(
                "No config found for social intent '%s', language=%s",
                context.current_intent,
                lang,
            )
            return self._create_fallback_response(context)

        return {
            **context.result,
            "intent": context.current_intent,
            "response": self._build_response(context, config),
            "entities": self._build_entities(context),
        }

    def _build_response(self, context: SocialContext, config: Dict) -> str:
        """Construct formatted social response"""
        lang = self.lm.normalize_language(context.language)
        templates = config.get("responses", [])
        if not templates:
            logger.warning(
                "No templates found for intent=%s, language=%s, using fallback",
                context.current_intent,
                lang,
            )
            try:
                response = self.lm.get_fallback_response(lang, context.current_intent)
            except Exception as e:
                logger.error(
                    "Failed to get fallback response for '%s', language=%s: %s",
                    context.current_intent,
                    lang,
                    str(e),
                )
                response = "Unknown response."

            logger.info("Selected response: %s", response)
            return response

        emoji = choice(self.EMOJI_MAP.get(context.current_intent, [""]))
        first_name = self._extract_first_name(context.user_name, context.email)
        response = choice(templates).format(
            name=first_name,
            emoji=emoji,
            time=self._get_local_time(lang),
        )
        logger.info("Selected response: %s", response)
        return response

    def _build_entities(self, context: SocialContext) -> Dict[str, Any]:
        """Extract relevant entities from context"""
        entities = {
            "user": context.user_name,
            "email": context.email,
            "timestamp": datetime.now(pytz.utc).isoformat(),
        }
        logger.debug("Built entities: %s", entities)
        return entities

    def _extract_first_name(self, user_name: str, email: str) -> str:
        """Extract first name from user information"""
        if user_name:
            first_name = user_name.split()[0]
        else:
            first_name = email.split("@")[0]
        logger.debug("Extracted first name: %s", first_name)
        return first_name

    def _get_local_time(self, language: str) -> str:
        """Get localized time string based on language"""
        lang = self.lm.normalize_language(language)
        now = datetime.now(pytz.utc)

        # Language-specific time formats
        time_formats = {
            "en": "%I:%M %p",  # 12-hour with AM/PM (e.g., 02:30 PM)
            "ru": "%H:%M",  # 24-hour (e.g., 14:30)
            "tj": "%H:%M",  # 24-hour (e.g., 14:30)
        }
        time_format = time_formats.get(lang, "%H:%M")

        formatted_time = now.strftime(time_format)
        logger.debug("Formatted time for language=%s: %s", lang, formatted_time)
        return formatted_time

    def _create_error_response(self, context: SocialContext) -> Dict[str, Any]:
        """Create error response for social interactions"""
        lang = self.lm.normalize_language(context.language)
        logger.debug("Creating error response for language: %s", lang)
        try:
            error_msg = self.lm.get_fallback_response(lang, "error")
        except Exception as e:
            logger.error(
                "Failed to get fallback error response, language=%s: %s", lang, str(e)
            )
            error_msg = "Unknown error occurred."

        logger.info("Selected error response: %s", error_msg)
        return {**context.result, "intent": "social_error", "response": error_msg}

    def _create_fallback_response(self, context: SocialContext) -> Dict[str, Any]:
        """Create fallback response when config is missing"""
        lang = self.lm.normalize_language(context.language)
        logger.debug(
            "Creating fallback response for intent=%s, language=%s",
            context.current_intent,
            lang,
        )
        try:
            response = self.lm.get_fallback_response(lang, context.current_intent)
        except Exception as e:
            logger.error(
                "Failed to get fallback response for '%s', language=%s: %s",
                context.current_intent,
                lang,
                str(e),
            )
            response = "Unknown response."

        logger.info("Selected fallback response: %s", response)
        return {
            **context.result,
            "intent": context.current_intent,
            "response": response,
            "entities": self._build_entities(context),
        }
