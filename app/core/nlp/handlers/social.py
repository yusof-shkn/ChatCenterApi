import re
from random import choice
from typing import Dict, Any
from datetime import datetime
import pytz


class SocialHandler:
    def __init__(self, intent_configs: Dict[str, Dict[str, Any]]):
        """Initialize with a dictionary of configs keyed by language."""
        self.configs = intent_configs  # e.g., {"en": {...}, "ru": {...}, "tg": {...}}
        self.emoji_map = {
            "greeting": ["👋", "😊", "🌞", "🖐️"],
            "farewell": ["👋", "👍", "😊", "✨"],
        }
        self.lang_map = {"english": "en", "russian": "ru", "tajiki": "tg"}

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
        if current_intent in ["greeting", "farewell"]:
            return await self._handle_social_intent(
                language, user_name, email, current_intent, result
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
        # Map language to YAML config key
        config_key = self.lang_map.get(language, "en")
        # Fallback to English if language config is missing
        config = self.configs.get(config_key, self.configs.get("en", {}))
        if intent_type not in config:
            return result  # Return unchanged result if intent not found

        emoji = choice(self.emoji_map[intent_type])
        templates = config[intent_type]["responses"]
        first_name = user_name.split()[0] if user_name else email.split("@")[0]
        response = choice(templates).format(name=first_name, emoji=emoji)

        return {
            **result,
            "intent": intent_type,
            "response": response,
            "entities": {"user": user_name, "email": email},
        }
