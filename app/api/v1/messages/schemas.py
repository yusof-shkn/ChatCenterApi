from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class MessageResponse(BaseModel):
    text: str
    response: str
    timestamp: datetime

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
