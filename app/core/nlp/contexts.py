# app/core/nlp/contexts.py
from dataclasses import dataclass
from typing import Dict, Any
import uuid
from datetime import datetime


@dataclass
class BaseContext:
    user_id: uuid.UUID
    user_name: str
    email: str
    text: str
    language: str
    current_intent: str
    entities: Dict[str, Any]
    prev_intent: str
    prev_entities: Dict[str, Any]
    retry_count: int
    result: Dict[str, Any]
    timestamp: datetime


@dataclass
class SocialContext(BaseContext):
    pass


@dataclass
class WeatherContext(BaseContext):
    pass


@dataclass
class SupportContext(BaseContext):
    pass


@dataclass
class CompanyContext(BaseContext):
    pass
