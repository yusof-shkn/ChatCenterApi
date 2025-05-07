# app/core/nlp_models/english.py
import spacy
from spacy.matcher import Matcher
from spacy.pipeline import EntityRuler
from pathlib import Path
from app.core.config import settings
from ..schemas import IntentConfig
from ..utils import load_yaml_config


def load_english():
    # 1) Load the base model
    nlp = spacy.load(settings.NLP_MODEL_NAME)

    # 2) Register the built-in EntityRuler factory BEFORE the 'ner' step
    #    — note we pass the factory name, not the object itself
    nlp.add_pipe("entity_ruler", before="ner", config={"overwrite_ents": True})

    # 3) Now retrieve that pipe and add your custom patterns
    ruler = nlp.get_pipe("entity_ruler")
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
    matcher = Matcher(nlp.vocab)
    data = load_yaml_config(Path(settings.BASE_DIR) / "config" / "intents_en.yaml")

    intent_configs = {}
    for name, cfg in data.items():
        # convert patterns to spaCy token patterns
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

        # add to matcher (GPE in provide_city triggers city intent)
        if name == "provide_city":
            matcher.add(name, [[{"ENT_TYPE": {"IN": ["GPE", "LOC"]}}]])
        else:
            matcher.add(name, processed)

    return nlp, matcher, intent_configs
