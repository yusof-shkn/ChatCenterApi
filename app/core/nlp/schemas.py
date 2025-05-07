from pydantic import BaseModel
from typing import List, Optional


class IntentConfig(BaseModel):
    patterns: List[List[dict]]
    responses: List[str]
    context: Optional[dict] = None
    requires_entities: Optional[List[str]] = None
