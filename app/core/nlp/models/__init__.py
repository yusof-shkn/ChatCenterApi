import logging
from typing import Tuple, Dict

from app.core.config import settings
from .english import load_english
from .tajiki import load_tajiki
from .russian import load_russian

logger = logging.getLogger(__name__)

# Map of language keys → loader functions
_LOADERS: Dict[str, callable] = {
    "english": load_english,
    "tajiki": load_tajiki,
    "russian": load_russian,
}


def get_nlp_pipeline(lang_key: str) -> Tuple:
    """
    Return (nlp, matcher, intent_configs) for the given lang_key,
    logging each step and erroring if no loader is found.
    """
    logger.debug("Requesting NLP pipeline for key '%s'", lang_key)

    loader = _LOADERS.get(lang_key)
    if not loader:
        valid = ", ".join(_LOADERS.keys())
        logger.error(
            "No NLP loader configured for language '%s' (valid: %s)",
            lang_key,
            valid,
        )
        raise ValueError(f"No loader for language '{lang_key}'. Valid choices: {valid}")

    try:
        nlp, matcher, intent_configs = loader()
        logger.info(
            "Loaded NLP pipeline '%s': nlp=%r, matcher=%r, intents=%d",
            lang_key,
            type(nlp).__name__,
            type(matcher).__name__,
            len(intent_configs),
        )
    except Exception as e:
        logger.exception("Error loading NLP pipeline for '%s': %s", lang_key, e)
        raise

    return nlp, matcher, intent_configs
