from pathlib import Path
import yaml
from typing import Dict

import logging

logger = logging.getLogger(__name__)


def load_yaml_config(path: Path) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except UnicodeDecodeError as e:
        logger.error("Failed to read YAML %s: %s", path, e)
        raise RuntimeError(f"Cannot read config file {path}; ensure it's UTF‑8 encoded")
