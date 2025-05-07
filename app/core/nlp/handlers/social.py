import re
from random import choice
from typing import Dict, Any
from datetime import datetime
import pytz
import logging

logger = logging.getLogger(__name__)


class SocialHandler:
    def __init__(self, intent_configs: Dict[str, Dict[str, Any]]):
        self.configs = intent_configs
        self.lang_map = {"en": "en", "ru": "ru", "tg": "tg"}  # Simplified mapping
        self.emoji_map = {
            "greeting": ["👋", "😊", "🌞", "🖐️"],
            "farewell": ["👋", "👍", "😊", "✨"],
        }

    async def handle(
        self,
        language: str,
        user_name: str,
        email: str,
        text: str,
        current_intent: str,
        entities: Dict[str, Any],
        prev_intent: str,
        prev_entities: Dict[str, Any],
        retry_count: int,
        result: Dict[str, Any],
    ) -> Dict[str, Any]:
        lang_code = self.lang_map.get(language.lower(), "en")
        logger.debug(f"SocialHandler received language: {lang_code}")
        if current_intent in ["greeting", "farewell"]:
            return await self._handle_social_intent(
                lang_code, user_name, email, current_intent, result
            )
        return result

    async def _handle_social_intent(
        self,
        language: str,
        user_name: str,
        email: str,
        intent_type: str,
        result: Dict[str, Any],
    ):
        # Normalize language code
        lang_code = self.lang_map.get(language.lower(), "en")
        logger.debug(f"Normalized language code: {lang_code}")

        # Get config for normalized language code
        config = self.configs.get(lang_code, self.configs.get("en", {}))
        logger.debug(f"Config keys: {list(config.keys())}")

        if intent_type not in config:
            logger.warning(f"Intent {intent_type} not found in {lang_code} config")
            return result

        try:
            emoji = choice(self.emoji_map[intent_type])
            templates = config[intent_type]["responses"]
            first_name = user_name.split()[0] if user_name else email.split("@")[0]

            logger.debug(f"Available templates: {templates}")
            response = choice(templates).format(name=first_name, emoji=emoji)
            logger.debug(f"Formatted response: {response}")

            return {
                **result,
                "intent": intent_type,
                "response": response,
                "entities": {"user": user_name, "email": email},
            }
        except Exception as e:
            logger.error(f"Social intent failed: {str(e)}")
            return result
