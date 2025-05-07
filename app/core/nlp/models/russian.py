import spacy
from spacy.matcher import Matcher
from spacy.pipeline import EntityRuler
from pathlib import Path
from app.core.config import settings
from ..schemas import IntentConfig
from ..utils import load_yaml_config


def load_russian():
    # Load enhanced Russian model with Tajik support
    nlp = spacy.load("ru_core_news_md")

    # Multilingual entity ruler
    ruler = nlp.add_pipe("entity_ruler", before="ner", config={"overwrite_ents": True})
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
    matcher = Matcher(nlp.vocab)
    data = load_yaml_config(Path(settings.BASE_DIR) / "config" / "intents_ru.yaml")
    intent_configs = {}

    for name, cfg in data.items():
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
            matcher.add(
                name,
                [
                    [{"ENT_TYPE": "GPE"}],
                    [{"LEMMA": "погода"}, {"ENT_TYPE": "GPE"}],
                    [{"ENT_TYPE": "WEATHER_CONDITION"}, {"ENT_TYPE": "GPE"}],
                ],
            )
        else:
            matcher.add(name, processed)

    return nlp, matcher, intent_configs
