import spacy
from spacy.matcher import Matcher
from spacy.pipeline import EntityRuler
from pathlib import Path
from app.core.config import settings
from ..schemas import IntentConfig
from ..utils import load_yaml_config
import logging

logger = logging.getLogger(__name__)


def load_multi_language():
    try:
        nlp = spacy.load("xx_ent_wiki_sm")
    except Exception as e:
        logger.error("Failed to load spacy.blank('tg'): %s", e)
        raise ValueError("Unable to initialize Multi language NLP model")

    try:
        # Add EntityRuler before NER
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

        # Set up the intent matcher
        matcher = Matcher(nlp.vocab)
        config_path = Path(settings.BASE_DIR) / "config" / "intents_tg.yaml"
        if not config_path.exists():
            logger.error("Multi language config file not found: %s", config_path)
            raise FileNotFoundError(
                f"Multi language config file not found: {config_path}"
            )
        data = load_yaml_config(config_path)
        if not data:
            logger.error(
                "Multi language config file is empty or invalid: %s", config_path
            )
            raise ValueError(
                f"Multi language config file is empty or invalid: {config_path}"
            )

        intent_configs = {}
        for name, cfg in data.items():
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

                # Special handling for provide_city intent
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
    except Exception as e:
        logger.error("Failed to load Multi language pipeline: %s", e)
        raise
