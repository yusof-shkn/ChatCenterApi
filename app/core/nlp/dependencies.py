import logging
from pathlib import Path
import yaml
from app.core.config import settings
from app.core.nlp.handlers.weather import WeatherHandler
from app.core.nlp.handlers.support import SupportHandler
from app.core.nlp.handlers.comany import CompanyHandler
from app.core.nlp.handlers.social import SocialHandler
from app.core.nlp.utils import load_yaml_config

logger = logging.getLogger(__name__)


def load_intent_section(intent_name: str, lang: str) -> dict:
    config_path = Path(settings.BASE_DIR) / "config" / f"intents_{lang}.yaml"
    logger.debug("Loading intent '%s' from %s", intent_name, config_path)
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            full_config = yaml.safe_load(f)
        if not full_config:
            logger.warning("Config file %s is empty or invalid", config_path)
            return {}
        result = full_config.get(intent_name, {})
        if result:
            logger.debug("Found intent '%s' in %s", intent_name, config_path)
        else:
            logger.debug("Intent '%s' not found in %s", intent_name, config_path)
        return result
    except FileNotFoundError:
        logger.error("Config file not found: %s", config_path)
        return {}
    except yaml.YAMLError as e:
        logger.error("Failed to parse YAML file %s: %s", config_path, e)
        return {}
    except Exception as e:
        logger.error("Unexpected error loading %s: %s", config_path, e)
        return {}


def get_weather_handler() -> WeatherHandler:
    logger.info("Initializing WeatherHandler")
    weather_configs = {}
    for lang in ["en", "ru", "tg"]:
        logger.debug("Loading weather config for language '%s'", lang)
        weather_configs[lang] = load_intent_section("weather", lang)
    if not any(weather_configs.values()):
        logger.error("No valid weather intent configs found for any language")
        raise ValueError("No weather intent found in any language config")
    logger.info(
        "WeatherHandler initialized with configs for %s", list(weather_configs.keys())
    )
    return WeatherHandler(intent_configs=weather_configs)


def get_support_handler() -> SupportHandler:
    logger.info("Initializing SupportHandler")
    support_configs = {}
    for lang in ["en", "ru", "tg"]:
        logger.debug("Loading support config for language '%s'", lang)
        support_configs[lang] = load_intent_section("support", lang)
    if not any(support_configs.values()):
        logger.error("No valid support intent configs found for any language")
        raise ValueError("No support intent found in any language config")
    logger.info(
        "SupportHandler initialized with configs for %s", list(support_configs.keys())
    )
    return SupportHandler(intent_configs=support_configs)


def get_company_handler() -> CompanyHandler:
    logger.info("Initializing CompanyHandler")
    company_configs = {}
    for lang in ["en", "ru", "tg"]:
        logger.debug("Loading company config for language '%s'", lang)
        company_configs[lang] = load_intent_section("company", lang)
    if not any(company_configs.values()):
        logger.error("No valid company intent configs found for any language")
        raise ValueError("No company intent found in any language config")
    logger.info(
        "CompanyHandler initialized with configs for %s", list(company_configs.keys())
    )
    return CompanyHandler(intent_configs=company_configs)


def get_social_handler() -> SocialHandler:
    logger.info("Initializing SocialHandler")
    social_configs = {}
    for lang in ["en", "ru", "tg"]:
        logger.debug("Loading social intents for language '%s'", lang)
        try:
            data = load_yaml_config(
                Path(settings.BASE_DIR) / "config" / f"intents_{lang}.yaml"
            )
            if not data:
                logger.warning("No data loaded from intents_%s.yaml", lang)
                continue
            social_intents = {
                intent: data[intent]
                for intent in ["greeting", "farewell"]
                if intent in data
            }
            if social_intents:
                social_configs[lang] = social_intents
                logger.debug(
                    "Loaded social intents for %s: %s",
                    lang,
                    list(social_intents.keys()),
                )
            else:
                logger.debug(
                    "No social intents (greeting, farewell) found for %s", lang
                )
        except Exception as e:
            logger.error("Failed to load social intents for %s: %s", lang, e)
            continue
    if not social_configs:
        logger.error("No valid social intent configs found for any language")
        raise ValueError("No social intents found in any language config")
    logger.info(
        "SocialHandler initialized with configs for %s", list(social_configs.keys())
    )
    return SocialHandler(intent_configs=social_configs)
