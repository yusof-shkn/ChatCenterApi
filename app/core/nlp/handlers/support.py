import re
from random import choice
from typing import Dict, Any


# SupportHandler
class SupportHandler:
    """
    Handles 'support' and 'help' related intents with multi-turn follow-up logic,
    supporting multiple languages.
    """

    def __init__(self, intent_configs: Dict[str, Dict[str, Any]]):
        self.configs = intent_configs  # e.g., {"en": {...}, "ru": {...}, "tg": {...}}

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
        if current_intent != "support":
            return result

        config = self.configs.get(language, self.configs.get("en", {}))
        base_responses = config.get("responses", [])

        if prev_intent != "support" and retry_count == 0:
            return {
                **result,
                "intent": "support",
                "response": choice(base_responses),
                "retry_count": 1,
            }

        category = self._detect_category(language, text)
        cat_cfg = config.get("followups", {}).get(
            category, config.get("followups", {}).get("other", {})
        )

        asked_key = f"_support_asked_{category}"
        if not prev_entities.get(asked_key):
            updated_entities = {**entities, asked_key: True}
            return {
                **result,
                "intent": "support_followup",
                "response": cat_cfg.get("question", "Can you give me more details?"),
                "entities": updated_entities,
            }

        return {
            **result,
            "intent": "support_resolution",
            "response": choice(
                cat_cfg.get("responses", ["Let me know if that helps."])
            ),
        }

    def _detect_category(self, language: str, text: str) -> str:
        """Detects support category based on keywords in the specified language"""
        config = self.configs.get(language, self.configs.get("en", {}))
        text_lower = text.lower()
        for category, cfg in config.get("followups", {}).items():
            for kw in cfg.get("keywords", []):
                if re.search(rf"\b{re.escape(kw)}\b", text_lower):
                    return category
        return "other"
