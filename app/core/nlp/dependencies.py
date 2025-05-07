from pathlib import Path
import yaml
from app.core.config import settings
from app.core.nlp.handlers.weather import WeatherHandler
from app.core.nlp.handlers.support import SupportHandler
from app.core.nlp.handlers.comany import CompanyHandler
from app.core.nlp.handlers.social import SocialHandler
from app.core.nlp.utils import load_yaml_config


def load_intent_section(intent_name: str, lang: str) -> dict:
    config_path = Path(settings.BASE_DIR) / "config" / f"intents_{lang}.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        full_config = yaml.safe_load(f)
    return full_config.get(intent_name, {})


def get_weather_handler() -> WeatherHandler:
    weather_configs = {}
    for lang in ["en", "ru", "tg"]:
        weather_configs[lang] = load_intent_section("weather", lang)
    if not any(weather_configs.values()):
        raise ValueError("No weather intent found in any language config")
    return WeatherHandler(intent_configs=weather_configs)


def get_support_handler() -> SupportHandler:
    support_configs = {}
    for lang in ["en", "ru", "tg"]:
        support_configs[lang] = load_intent_section("support", lang)
    if not any(support_configs.values()):
        raise ValueError("No support intent found in any language config")
    return SupportHandler(intent_configs=support_configs)


def get_company_handler() -> CompanyHandler:
    company_configs = {}
    for lang in ["en", "ru", "tg"]:
        company_configs[lang] = load_intent_section("company", lang)
    if not any(company_configs.values()):
        raise ValueError("No company intent found in any language config")
    return CompanyHandler(intent_configs=company_configs)


def get_social_handler() -> SocialHandler:
    social_configs = {}
    for lang in ["en", "ru", "tg"]:
        data = load_yaml_config(
            Path(settings.BASE_DIR) / "config" / f"intents_{lang}.yaml"
        )
        social_intents = {
            intent: data[intent]
            for intent in ["greeting", "farewell"]
            if intent in data
        }
        if social_intents:
            social_configs[lang] = social_intents
    ...
    return SocialHandler(intent_configs=social_configs)
