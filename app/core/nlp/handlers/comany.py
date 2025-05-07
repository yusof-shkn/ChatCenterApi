from typing import Dict, Any, Optional, List, Tuple
from random import choice
import re
from app.core.weather import get_city_weather

# CompanyHandler
class CompanyHandler:
    """
    Dynamically handles the 'company' intent, providing detailed information
    about the company's services, history, mission, and more in multiple languages.
    """
    def __init__(self, intent_configs: Dict[str, Dict[str, Any]]):
        """Initialize with a dictionary of configs keyed by language."""
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
        if current_intent == "company":
            config = self.configs.get(language, self.configs.get("en", {}))
            if entities.get("specific_info"):
                return await self.provide_detailed_info(language, entities)

            responses = config.get("responses", [])
            response = choice(responses) if responses else "We provide innovative technology solutions."
            return {
                **result,
                "intent": "company",
                "response": response,
            }
        return result

    async def provide_detailed_info(self, language: str, entities: Dict[str, Any]) -> Dict[str, Any]:
        """Provides detailed company information based on entities and language"""
        config = self.configs.get(language, self.configs.get("en", {}))
        info_type = entities.get("specific_info", "")
        if info_type == "services":
            return self.get_service_details(language)
        elif info_type == "history":
            return self.get_company_history(language)
        elif info_type == "mission":
            return self.get_company_mission(language)
        return {
            "intent": "company",
            "response": config.get("default_response", "I'm sorry, I don't have information on that."),
        }

    def get_service_details(self, language: str) -> Dict[str, str]:
        """Returns detailed service information in the specified language"""
        config = self.configs.get(language, self.configs.get("en", {}))
        services = config.get("services", [])
        service_details = choice(services) if services else "Our services include various technology solutions."
        return {
            "intent": "company",
            "response": service_details,
        }

    def get_company_history(self, language: str) -> Dict[str, str]:
        """Returns company history information in the specified language"""
        config = self.configs.get(language, self.configs.get("en", {}))
        history = config.get("company_facts", {}).get("history", "Our company was founded with a vision.")
        return {"intent": "company", "response": history}

    def get_company_mission(self, language: str) -> Dict[str, str]:
        """Returns company mission statement in the specified language"""
        config = self.configs.get(language, self.configs.get("en", {}))
        mission = config.get("company_facts", {}).get("mission", "Our mission is to empower businesses.")
        return {"intent": "company", "response": mission}
