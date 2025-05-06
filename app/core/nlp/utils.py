from pathlib import Path
import yaml
from typing import Dict


def load_yaml_config(file_path: Path) -> Dict:
    """Load YAML configuration file"""
    try:
        with open(file_path, "r") as f:
            return yaml.safe_load(f)
    except Exception as e:
        raise RuntimeError(f"Failed to load YAML config: {str(e)}")
