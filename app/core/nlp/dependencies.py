from pathlib import Path
from app.core.config import settings
from .language.config import LanguageConfig, DetectionConfig
from .language.loader import IntentLoader
from .language.manager import LanguageManager
from .language.detector import ScriptDetector, LanguageDetector
from .services import NLPService
from .handlers import IntentRouter

# Define fallbacks separately for better maintainability
FALLBACKS = {
    "en": {
        "general": ["Please rephrase that"],
        "error": "An error occurred",
    },
    "ru": {
        "general": ["Пожалуйста, перефразируйте это"],
        "error": "Произошла ошибка",
    },
    "tg": {
        "general": ["Илтимос, инро дигар карда гӯед"],
        "error": "Хато рух дод",
    },
}


def get_language_config():
    return LanguageConfig(
        code="en",
        name="english",
        fallbacks=FALLBACKS,
        aliases={
            "en": "en",
            "ru": "ru",
            "tg": "tg",
            "english": "en",
            "russian": "ru",
            "tajik": "tg",
        },
        config_path=Path(settings.BASE_DIR) / "config",
    )


def get_intent_loader():
    return IntentLoader(get_language_config().config_path)


def get_language_manager():
    return LanguageManager(config=get_language_config(), loader=get_intent_loader())


def get_detection_config():
    return DetectionConfig(
        tajik_chars={"Ғ", "ғ", "Ӯ", "ӯ", "Қ", "қ", "Ҳ", "ҳ", "Ҷ", "ҷ", "Ӣ", "ӣ"},
        script_threshold=0.8,
        max_input_length=500,
        russian_words={"но", "или", "если", "чтобы", "когда"},
        tajik_words={"ва", "ё", "ҳангоми", "то", "ки"},
    )


def get_script_detector():
    return ScriptDetector(get_detection_config())


def get_language_detector():
    return LanguageDetector(get_detection_config(), get_script_detector())


def get_nlp_service():
    return NLPService(
        language_manager=get_language_manager(),
        language_detector=get_language_detector(),
        script_detector=get_script_detector(),
    )


def get_intent_router() -> IntentRouter:
    return IntentRouter(
        LanguageManager(config=get_language_config(), loader=get_intent_loader())
    )
