from typing import Dict, Any
import logging
from dataclasses import dataclass
from random import choice
from app.core.nlp.language.manager import LanguageManager
from app.core.nlp.contexts import WeatherContext
import httpx

logger = logging.getLogger(__name__)


class WeatherHandler:
    def __init__(self, language_manager: LanguageManager):
        self.lm = language_manager
        logger.info("Initialized WeatherHandler with LanguageManager")

    async def handle(self, context: WeatherContext) -> Dict[str, Any]:
        """Main entry point for weather intent processing"""
        logger.debug(
            "Handling weather context: text=%s, language=%s, current_intent=%s",
            context.text,
            context.language,
            context.current_intent,
        )
        try:
            if not self._should_handle(context):
                logger.debug("WeatherHandler not handling context")
                return context.result

            self._update_city_from_text(context)

            if not context.entities.get("city"):
                result = await self._handle_missing_city(context)
            else:
                result = await self._handle_weather_request(context)

            logger.info(
                "Weather request processed: intent=%s, response=%s",
                result.get("intent", "unknown"),
                result.get("response", "none"),
            )
            return result

        except Exception as e:
            logger.error("Weather handling failed: %s", str(e))
            error_response = self._create_error_response(context)
            logger.info(
                "Returning error response: intent=%s, response=%s",
                error_response.get("intent", "unknown"),
                error_response.get("response", "none"),
            )
            return error_response

    def _should_handle(self, context: WeatherContext) -> bool:
        """Determine if weather handler should process this request"""
        should_handle = context.current_intent in ["weather", "weather_prompt"] or (
            context.prev_intent == "weather_prompt"
        )
        logger.debug(
            "Checking if should handle: current_intent=%s, prev_intent=%s, should_handle=%s",
            context.current_intent,
            context.prev_intent,
            should_handle,
        )
        return should_handle

    def _update_city_from_text(self, context: WeatherContext):
        """Extract city from text if previous prompt"""
        if context.prev_intent == "weather_prompt" and not context.entities.get("city"):
            context.entities["city"] = context.text.strip()
            logger.debug("Updated city from text: %s", context.entities["city"])

    async def _handle_missing_city(self, context: WeatherContext) -> Dict[str, Any]:
        """Handle case where city is not provided"""
        lang = self.lm.normalize_language(context.language)
        logger.debug("Normalized language: %s", lang)
        config = self.lm.get_intent_config("weather_prompt", lang)
        logger.debug("Retrieved config for weather_prompt: %s", config)

        responses = config.get("responses")
        if not responses:
            logger.warning(
                "No responses found in config for weather_prompt, language=%s", lang
            )
            try:
                responses = [self.lm.get_fallback_response(lang, "prompt")]
            except Exception as e:
                logger.warning(
                    "Failed to get fallback response for 'prompt': %s", str(e)
                )
                default_responses = {
                    "en": ["Please provide a city name."],
                    "ru": ["Пожалуйста, укажите название города."],
                    "tj": ["Лутфан, номи шаҳрро пешниҳод кунед."],
                }
                responses = default_responses.get(lang, default_responses["en"])

        response = choice(responses)
        logger.info("Selected response for missing city: %s", response)
        return {
            **context.result,
            "intent": "weather_prompt",
            "response": response,
            "retry_count": context.retry_count + 1,
            "entities": context.entities,
        }

    async def _handle_weather_request(self, context: WeatherContext) -> Dict[str, Any]:
        """Process valid weather request with city"""
        lang = self.lm.normalize_language(context.language)
        city = context.entities["city"]
        time = context.entities.get("time", "today")
        logger.debug(
            "Handling weather request: city=%s, time=%s, language=%s", city, time, lang
        )

        try:
            weather_data = await get_city_weather(city, time)
            if not weather_data:
                logger.warning("No weather data returned for city=%s", city)
                weather_data = {"description": "unknown", "temperature": "N/A"}
            return self._create_success_response(context, city, time, weather_data)
        except ValueError as e:
            logger.warning("Weather validation error: %s", str(e))
            return self._create_validation_error(context, str(e))
        except Exception as e:
            logger.error("Weather API error: %s", str(e))
            return self._create_error_response(context)

    def _create_success_response(
        self, context: WeatherContext, city: str, time: str, weather_data: Dict
    ) -> Dict[str, Any]:
        """Create successful weather response"""
        lang = self.lm.normalize_language(context.language)
        config = self.lm.get_intent_config("weather_response", lang)
        logger.debug("Retrieved config for weather_response: %s", config)

        templates = config.get("responses")
        if not templates:
            logger.warning(
                "No response templates found for weather_response, language=%s", lang
            )
            default_templates = {
                "en": ["The weather in {city} is {description} with {temp}°C"],
                "ru": ["Погода в {city} {description}, температура {temp}°C"],
                "tj": ["Обу ҳаво дар {city} {description}, ҳарорат {temp}°C"],
            }
            templates = default_templates.get(lang, default_templates["en"])

        response = choice(templates).format(
            city=city,
            time=time,
            description=weather_data.get("description", "unknown"),
            temp=weather_data.get("temperature", "N/A"),
        )
        logger.info("Selected success response: %s", response)
        return {
            **context.result,
            "intent": "weather",
            "response": response,
            "entities": {"city": city, "time": time},
        }

    def _create_validation_error(
        self, context: WeatherContext, error_msg: str
    ) -> Dict[str, Any]:
        """Create validation error response"""
        lang = self.lm.normalize_language(context.language)
        default_error_msgs = {
            "en": f"{error_msg}. Please enter a valid city name.",
            "ru": f"{error_msg}. Пожалуйста, введите действительное название города.",
            "tj": f"{error_msg}. Лутфан, номи шаҳри дуруст ворид кунед.",
        }
        response = default_error_msgs.get(lang, default_error_msgs["en"])
        logger.info("Selected validation error response: %s", response)
        return {
            **context.result,
            "intent": "weather_prompt",
            "response": response,
            "retry_count": context.retry_count + 1,
        }

    def _create_error_response(self, context: WeatherContext) -> Dict[str, Any]:
        """Create generic error response"""
        lang = self.lm.normalize_language(context.language)
        try:
            error_msg = self.lm.get_fallback_response(lang, "error")
        except Exception:
            logger.warning(
                "Failed to get fallback error response for language=%s", lang
            )
            default_error_msgs = {
                "en": "Sorry, something went wrong while fetching the weather for {city}.",
                "ru": "Извините, произошла ошибка при получении погоды для {city}.",
                "tj": "Бубахшед, ҳангоми гирифтани обу ҳаво барои {city} хатогӣ рух дод.",
            }
            error_msg = default_error_msgs.get(lang, default_error_msgs["en"])

        response = error_msg.format(
            city=context.entities.get("city", "unknown location")
        )
        logger.info("Selected error response: %s", response)
        return {
            **context.result,
            "intent": "weather_error",
            "response": response,
            "entities": context.entities,
        }


async def get_city_weather(city: str, time: str = "today") -> Dict[str, Any]:
    """
    Fetches weather with better error handling, time parameter usage, and validation.
    Returns None if the API call fails completely, allowing default value usage in the handler.
    """
    logger.debug("Fetching weather for city=%s, time=%s", city, time)
    try:
        url = f"https://wttr.in/{city}"
        params = {"format": "j1"}

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

        if not isinstance(data.get("current_condition"), list) or not isinstance(
            data.get("weather"), list
        ):
            raise ValueError("Invalid API response format")

        if time == "today":
            weather = data["weather"][0]
        elif time == "tomorrow":
            weather = data["weather"][1]
        else:
            raise ValueError(f"Invalid time parameter: {time}")

        weather_data = {
            "description": weather["hourly"][0]["weatherDesc"][0]["value"],
            "temperature": weather["hourly"][0]["tempC"],
        }
        logger.debug("Retrieved weather data: %s", weather_data)
        return weather_data

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise ValueError(f"Location '{city}' not found")
        logger.error("HTTP error fetching weather: %s", str(e))
        return None
    except (KeyError, IndexError, ValueError) as e:
        logger.warning("Weather data parsing error: %s", str(e))
        raise ValueError(f"Could not parse weather data: {str(e)}")
    except Exception as e:
        logger.error("Unexpected error in get_city_weather: %s", str(e))
        return None
