from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional
import uuid


class MessageLog(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    text: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    processed: bool = False
    intent: Optional[str] = None
    response: Optional[str] = None
    prev_intent: Optional[str] = None

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
        validate_by_name = True
