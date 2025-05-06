# app/core/nlp/factory.py

import logging
from .detector import detect_language
from .models import get_nlp_pipeline
from app.core.config import settings

logger = logging.getLogger(__name__)


def get_pipeline_for_text(text: str):
    """
    Detects the language of the input text, maps it to an internal key,
    and returns the (nlp, matcher, intent_configs) tuple for that language.
    """
    # 1) Detect language code
    code = detect_language(text)
    logger.debug("Detected language code '%s' for text: %r", code, text)

    # 2) Map to internal key
    mapping = {
        "en": "english",
        "ru": "russian",
        "tg": "tajiki",
    }
    key = mapping.get(code, settings.DEFAULT_LANGUAGE)
    logger.info("Mapped language code '%s' to pipeline key '%s'", code, key)

    # 3) Retrieve the pipeline
    try:
        nlp, matcher, intent_configs = get_nlp_pipeline(key)
        logger.debug(
            "Retrieved NLP pipeline for key '%s': nlp=%r, matcher=%r, intents=%d",
            key,
            type(nlp),
            type(matcher),
            len(intent_configs),
        )
    except Exception as e:
        logger.error(
            "Failed to load NLP pipeline for key '%s': %s", key, e, exc_info=True
        )
        raise

    return nlp, matcher, intent_configs
