from typing import Dict, List
from pydantic import BaseModel


class IntentConfig(BaseModel):
    patterns: List[str]
    responses: List[str]
