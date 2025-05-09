# core/nlp/language/
# ├── __init__.py
# ├── config.py
# ├── manager.py
# ├── detector.py
# └── loader.py

# core/nlp/language/config.py
from pathlib import Path
from typing import Dict, Any
from pydantic import BaseModel


class LanguageConfig(BaseModel):
    code: str
    name: str
    fallbacks: Dict[str, Any]
    aliases: Dict[str, str]
    config_path: Path


# class DetectionConfig(BaseModel):
#     tajik_chars: set = {"Ғ", "ғ", "Ӯ", "ӯ", "Қ", "қ", "Ҳ", "ҳ", "Ҷ", "ҷ", "Ӣ", "ӣ"}
#     script_threshold: float = 0.8
#     max_input_length: int = 500
#     russian_words: set = {"но", "или", "если", "чтобы", "когда"}
#     tajik_words: set = {"ва", "ё", "ҳангоми", "то", "ки"}


class DetectionConfig(BaseModel):
    script_threshold: float = 0.6
    max_input_length: int = 200
    russian_words: list[str] = []  # This should already exist
    tajik_weight: float = 1.5  # ← Add this
    russian_weight: float = 1.0  # ← Add this
