# app/core/nlp_models/tajiki.py
import spacy
from spacy.matcher import Matcher
from pathlib import Path
from app.core.config import settings
from ..schemas import IntentConfig
from ..utils import load_yaml_config


def load_tajiki():
    nlp = spacy.load("xx_ent_wiki_sm")
    matcher = Matcher(nlp.vocab)
    data = load_yaml_config(Path(settings.BASE_DIR) / "config" / "intents_tj.yaml")
    intent_configs = {}
    for name, cfg in data.items():
        intent_configs[name] = IntentConfig(**cfg)
        patterns = [[{"LOWER": t.lower()}] for t in cfg["patterns"]]
        matcher.add(name, patterns)
    return nlp, matcher, intent_configs
