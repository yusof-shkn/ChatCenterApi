import logging
import spacy
from spacy.matcher import Matcher
from spacy.pipeline import EntityRuler
from pathlib import Path
from app.core.config import settings
from ..schemas import IntentConfig
from ..utils import load_yaml_config

logger = logging.getLogger(__name__)


def load_russian():
    logger.info("Loading Russian NLP pipeline")
    try:
        # Load enhanced Russian model with Tajik support
        logger.debug("Loading spaCy model 'ru_core_news_md'")
        nlp = spacy.load("ru_core_news_md")
    except OSError as e:
        logger.error("Failed to load spaCy model 'ru_core_news_md': %s", e)
        raise ValueError("Unable to load spaCy model 'ru_core_news_md'")
    except Exception as e:
        logger.error("Unexpected error loading spaCy model 'ru_core_news_md': %s", e)
        raise

    try:
        # Multilingual entity ruler
        logger.debug("Adding EntityRuler pipe before 'ner'")
        ruler = nlp.add_pipe(
            "entity_ruler", before="ner", config={"overwrite_ents": True}
        )
        logger.debug("Adding entity patterns to EntityRuler")
        ruler.add_patterns(
            [
                # Russian cities
                {"label": "GPE", "pattern": [{"LOWER": "америка"}]},
                {"label": "GPE", "pattern": [{"LOWER": "душанбе"}]},
                {"label": "GPE", "pattern": [{"LOWER": "вахдат"}]},
                # Tajik cities and terms
                {"label": "GPE", "pattern": [{"LOWER": "ваҳдат"}]},
                {"label": "GPE", "pattern": [{"LOWER": "хӯҷанд"}]},
                {"label": "WEATHER", "pattern": [{"LOWER": "обу"}, {"LOWER": "ҳаво"}]},
                # Weather phenomena
                {"label": "WEATHER_CONDITION", "pattern": [{"LEMMA": "дождь"}]},
                {"label": "WEATHER_CONDITION", "pattern": [{"LEMMA": "снег"}]},
                {"label": "WEATHER_CONDITION", "pattern": [{"LOWER": "солнечно"}]},
            ]
        )

        # Context-aware intent matcher
        logger.debug("Loading intent configurations from intents_ru.yaml")
        config_path = Path(settings.BASE_DIR) / "config" / "intents_ru.yaml"
        data = load_yaml_config(config_path)
        if not data:
            logger.warning("Config file %s is empty or invalid", config_path)
            raise ValueError(f"Russian config file {config_path} is empty or invalid")

        logger.debug("Processing intent configurations")
        intent_configs = {}
        matcher = Matcher(nlp.vocab)
        for name, cfg in data.items():
            logger.debug("Processing intent '%s'", name)
            try:
                # Multilingual pattern processor
                processed = []
                for pattern in cfg["patterns"]:
                    doc = nlp(" ".join(pattern))
                    processed_pattern = []
                    for token in doc:
                        pattern_item = {"LEMMA": token.lemma_}
                        if token.lemma_ in ["погода", "дождь"]:
                            pattern_item["POS"] = "NOUN"
                        processed_pattern.append(pattern_item)
                    processed.append(processed_pattern)

                # Contextual response handler
                intent_configs[name] = IntentConfig(
                    patterns=processed,
                    responses=cfg["responses"],
                    context=cfg.get("context", {}),
                    requires_entities=cfg.get("requires_entities", []),
                    followups=cfg.get("followups", {}),
                )

                # Advanced pattern matching
                if name == "weather":
                    logger.debug(
                        "Adding advanced matcher patterns for 'weather' intent"
                    )
                    matcher.add(
                        name,
                        processed
                        + [
                            [{"ENT_TYPE": "WEATHER_CONDITION"}],
                            [{"LEMMA": "какой"}, {"LEMMA": "погода"}],
                            [{"LEMMA": "идти"}, {"ENT_TYPE": "WEATHER_CONDITION"}],
                        ],
                    )
                elif name == "provide_city":
                    logger.debug(
                        "Adding advanced matcher patterns for 'provide_city' intent"
                    )
                    matcher.add(
                        name,
                        [
                            [{"ENT_TYPE": "GPE"}],
                            [{"LEMMA": "погода"}, {"ENT_TYPE": "GPE"}],
                            [{"ENT_TYPE": "WEATHER_CONDITION"}, {"ENT_TYPE": "GPE"}],
                        ],
                    )
                else:
                    logger.debug("Adding matcher for intent '%s'", name)
                    matcher.add(name, processed)
            except Exception as e:
                logger.error("Failed to process intent '%s': %s", name, e)
                raise

        logger.info(
            "Russian NLP pipeline loaded successfully with %d intents",
            len(intent_configs),
        )
        return nlp, matcher, intent_configs

    except FileNotFoundError:
        logger.error("Config file not found: %s", config_path)
        raise
    except Exception as e:
        logger.error("Failed to load Russian pipeline: %s", e)
        raise
