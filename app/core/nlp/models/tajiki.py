import spacy
from spacy.matcher import Matcher
from spacy.pipeline import EntityRuler
from pathlib import Path
from app.core.config import settings
from ..schemas import IntentConfig
from ..utils import load_yaml_config
import logging

logger = logging.getLogger(__name__)


def load_tajiki():
    """Load Tajiki pipeline for intent detection and entity recognition."""
    # Load primary model (Russian model for Tajiki)
    try:
        nlp = spacy.load("ru_core_news_md")
    except Exception as e:
        logger.error("Failed to load spacy model 'ru_core_news_md': %s", e)
        raise ValueError("Unable to initialize Tajiki NLP model")

    # Add EntityRuler to primary model
    try:
        nlp.add_pipe("entity_ruler", before="ner", config={"overwrite_ents": True})
        ruler = nlp.get_pipe("entity_ruler")
        ruler.add_patterns(
            [
                {"label": "GPE", "pattern": "Душанбе"},  # Dushanbe
                {"label": "GPE", "pattern": "Ваҳдат"},  # Vahdat
                {"label": "GPE", "pattern": "Хучанд"},  # Khujand
                {"label": "GPE", "pattern": "Бишкек"},  # Bishkek
                {"label": "GPE", "pattern": [{"LOWER": "душанбе"}]},
                {"label": "GPE", "pattern": [{"LOWER": "ваҳдат"}]},
                {"label": "GPE", "pattern": [{"LOWER": "хучанд"}]},
                {"label": "GPE", "pattern": [{"LOWER": "бишкек"}]},
            ]
        )
    except Exception as e:
        logger.error("Failed to configure EntityRuler for model: %s", e)
        raise

    # Set up intent matcher
    matcher = Matcher(nlp.vocab)
    config_path = Path(settings.BASE_DIR) / "config" / "intents_tg.yaml"

    if not config_path.exists():
        logger.error("Tajiki config file not found: %s", config_path)
        raise FileNotFoundError(f"Tajiki config file not found: {config_path}")

    data = load_yaml_config(config_path)
    if not data:
        logger.error("Tajiki config file is empty or invalid: %s", config_path)
        raise ValueError(f"Tajiki config file is empty or invalid: {config_path}")

    intent_configs = {}
    for name, cfg in data.items():
        try:
            processed = [
                [{"LOWER": token.lower()} for token in pattern]
                for pattern in cfg["patterns"]
            ]
            # Validate context to ensure it's a dictionary
            context = cfg.get("context", {})
            if not isinstance(context, dict):
                logger.warning(
                    "Invalid context for intent '%s': expected dict, got %s. Defaulting to empty dict.",
                    name,
                    type(context).__name__,
                )
                context = {}
            intent_configs[name] = IntentConfig(
                patterns=processed,
                responses=cfg["responses"],
                context=context,
                requires_entities=cfg.get("requires_entities", []),
            )
            if name == "provide_city":
                matcher.add(name, [[{"ENT_TYPE": {"IN": ["GPE", "LOC"]}}]])
            else:
                matcher.add(name, processed)
        except Exception as e:
            logger.error(
                "Failed to process intent '%s' in intents_tg.yaml: %s", name, e
            )
            raise

    return nlp, matcher, intent_configs
