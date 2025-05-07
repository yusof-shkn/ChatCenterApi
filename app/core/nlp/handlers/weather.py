from typing import Dict, Any
from random import choice
from app.core.weather import get_city_weather
import logging

logger = logging.getLogger(__name__)


class WeatherHandler:
    """
    Handles weather-related conversation flow, prompting for missing cities
    and resolving full weather queries in multiple languages.
    """

    def __init__(self, intent_configs: Dict[str, Dict[str, Any]]):
        self.intent_configs = (
            intent_configs  # e.g., {"en": {...}, "ru": {...}, "tg": {...}}
        )
        self.fallback_responses = {
            "en": {
                "prompt": "Which city would you like the weather for?",
                "too_many_retries": "Please try asking again later.",
                "error": "Sorry, I couldn't retrieve the weather for {city}.",
            },
            "ru": {
                "prompt": "Для какого города хотите узнать погоду?",
                "too_many_retries": "Попробуйте спросить еще раз позже.",
                "error": "Извините, не удалось получить погоду для {city}.",
            },
            "tg": {
                "prompt": "Барои кадом шаҳр обу ҳаворо донистаниед?",
                "too_many_retries": "Лутфан баъдтар дубора пурсед.",
                "error": "Бубахшед, ман натавонистам обу ҳавои {city}-ро гирам.",
            },
        }

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
        city = entities.get("city") or prev_entities.get("city")
        time = entities.get("time") or prev_entities.get("time", "today")

        if not self._should_handle_weather(current_intent, prev_intent):
            return result

        if prev_intent == "weather_prompt" and not city:
            city = text.strip()
            entities = {**entities, "city": city}

        if not city:
            return self._handle_missing_city(language, retry_count, result)

        return await self._handle_valid_request(language, city, time, result)

    def _should_handle_weather(self, current_intent: str, prev_intent: str) -> bool:
        return current_intent == "weather" or (
            prev_intent == "weather_prompt" and current_intent == "provide_city"
        )

    def _handle_missing_city(
        self, language: str, retry_count: int, result: Dict[str, Any]
    ) -> Dict[str, Any]:
        config = self.intent_configs.get(language, self.intent_configs.get("en", {}))
        fallback = self.fallback_responses.get(language, self.fallback_responses["en"])

        if retry_count >= 2:
            return {
                **result,
                "intent": "unclear",
                "response": fallback["too_many_retries"],
            }
        return {
            **result,
            "intent": "weather_prompt",
            "response": choice(config.get("responses", [fallback["prompt"]])),
            "retry_count": retry_count + 1,
        }

    async def _handle_valid_request(
        self, language: str, city: str, time: str, result: Dict[str, Any]
    ) -> Dict[str, Any]:
        config = self.intent_configs.get(language, self.intent_configs.get("en", {}))
        fallback = self.fallback_responses.get(language, self.fallback_responses["en"])

        try:
            weather_info = await get_city_weather(city, time)
        except ValueError as e:
            logger.warning(f"Weather validation failed: {str(e)}")
            return {
                **result,
                "intent": "weather_prompt",
                "response": f"{str(e)}. Please enter a valid city name.",
                "retry_count": result.get("retry_count", 0) + 1,
            }
        except Exception as e:
            logger.error(f"Weather lookup failed: {str(e)}")
            weather_info = None

        if not isinstance(weather_info, dict):
            weather_info = {"description": "sunny", "temperature": 22}

        description = weather_info.get("description", "sunny")
        temp = weather_info.get("temperature", 22)

        try:
            provide_city_config = load_intent_section("provide_city", language)
            response_template = choice(
                provide_city_config.get("responses", [fallback["prompt"]])
            )
        except Exception as e:
            logger.error(f"Failed to load response template: {str(e)}")
            response_template = fallback["prompt"]

        return {
            **result,
            "intent": "weather",
            "response": response_template.format(
                city=city, time=time, description=description, temp=temp
            ),
            "entities": {"city": city, "time": time},
        }


def load_intent_section(intent_name: str, lang: str) -> dict:
    from pathlib import Path
    import yaml
    from app.core.config import settings

    # Normalize language codes
    lang_mapping = {
        "en": "en",
        "ru": "ru",
        "tg": "tg",
        "english": "en",
        "russian": "ru",
        "tajik": "tg",
    }
    lang_code = lang_mapping.get(lang.lower(), "en")

    config_path = Path(settings.BASE_DIR) / "config" / f"intents_{lang_code}.yaml"

    # Fallback chain: ru -> en
    if not config_path.exists():
        if lang_code == "tg":
            config_path = Path(settings.BASE_DIR) / "config" / "intents_ru.yaml"
        if not config_path.exists():
            config_path = Path(settings.BASE_DIR) / "config" / "intents_en.yaml"

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            full_config = yaml.safe_load(f)
        return full_config.get(intent_name, {})
    except Exception as e:
        logger.error(f"Config error: {str(e)}")
        return {}
