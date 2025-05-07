import logging
import spacy
from spacy.matcher import Matcher
from spacy.pipeline import EntityRuler
from pathlib import Path
from app.core.config import settings
from ..schemas import IntentConfig
from ..utils import load_yaml_config

logger = logging.getLogger(__name__)


def load_english():
    logger.info("Loading English NLP pipeline")
    try:
        # 1) Load the base model
        logger.debug("Loading spaCy model '%s'", settings.NLP_MODEL_NAME)
        nlp = spacy.load(settings.NLP_MODEL_NAME)
    except OSError as e:
        logger.error("Failed to load spaCy model '%s': %s", settings.NLP_MODEL_NAME, e)
        raise ValueError(f"Unable to load spaCy model '{settings.NLP_MODEL_NAME}'")
    except Exception as e:
        logger.error(
            "Unexpected error loading spaCy model '%s': %s", settings.NLP_MODEL_NAME, e
        )
        raise

    try:
        # 2) Register the built-in EntityRuler factory BEFORE the 'ner' step
        logger.debug("Adding EntityRuler pipe before 'ner'")
        nlp.add_pipe("entity_ruler", before="ner", config={"overwrite_ents": True})

        # 3) Now retrieve that pipe and add your custom patterns
        ruler = nlp.get_pipe("entity_ruler")
        logger.debug("Adding entity patterns to EntityRuler")
        ruler.add_patterns(
            [
                {"label": "GPE", "pattern": "Dushanbe"},
                {"label": "GPE", "pattern": "Vahdat"},
                {"label": "GPE", "pattern": "khujand"},
                {"label": "GPE", "pattern": "Bishkek"},
                {"label": "GPE", "pattern": [{"LOWER": "dushanbe"}]},
                {"label": "GPE", "pattern": [{"LOWER": "vahdat"}]},
                {"label": "GPE", "pattern": [{"LOWER": "khujand"}]},
                {"label": "GPE", "pattern": [{"LOWER": "bishkek"}]},
            ]
        )

        # 4) Build your intent matcher
        logger.debug("Loading intent configurations from intents_en.yaml")
        config_path = Path(settings.BASE_DIR) / "config" / "intents_en.yaml"
        data = load_yaml_config(config_path)
        if not data:
            logger.warning("Config file %s is empty or invalid", config_path)
            raise ValueError(f"English config file {config_path} is empty or invalid")

        logger.debug("Processing intent configurations")
        intent_configs = {}
        for name, cfg in data.items():
            logger.debug("Processing intent '%s'", name)
            try:
                # Convert patterns to spaCy token patterns
                processed = [
                    [{"LOWER": token.lower()} for token in pattern]
                    for pattern in cfg["patterns"]
                ]
                intent_configs[name] = IntentConfig(
                    patterns=processed,
                    responses=cfg["responses"],
                    context=cfg.get("context", {}),
                    requires_entities=cfg.get("requires_entities", []),
                )
            except Exception as e:
                logger.error("Failed to process intent '%s': %s", name, e)
                raise

        logger.debug("Building intent matcher with %d intents", len(intent_configs))
        matcher = Matcher(nlp.vocab)
        for name, config in intent_configs.items():
            if name == "provide_city":
                logger.debug("Adding special matcher for 'provide_city' intent")
                matcher.add(name, [[{"ENT_TYPE": {"IN": ["GPE", "LOC"]}}]])
            else:
                logger.debug("Adding matcher for intent '%s'", name)
                matcher.add(name, config.patterns)

        logger.info(
            "English NLP pipeline loaded successfully with %d intents",
            len(intent_configs),
        )
        return nlp, matcher, intent_configs

    except FileNotFoundError:
        logger.error("Config file not found: %s", config_path)
        raise
    except Exception as e:
        logger.error("Failed to load English pipeline: %s", e)
        raise
