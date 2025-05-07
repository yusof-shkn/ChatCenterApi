from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings
from app.models.mongo_models import MessageLog
from typing import List


class MongoDB:
    def __init__(self):
        self.client = None
        self.db = None

    async def connect(self):
        self.client = AsyncIOMotorClient(settings.MONGODB_URL)
        self.db = self.client[settings.MONGODB_NAME]

    async def close(self):
        if self.client:
            self.client.close()
            self.client = None
            self.db = None

    async def insert_message(self, message: MessageLog):
        return await self.db.messages.insert_one(message.dict(by_alias=True))

    async def init_mongo(self):
        self.client = AsyncIOMotorClient(settings.MONGODB_URL)
        self.db = self.client[settings.MONGODB_NAME]
        await self.client.admin.command("ping")
        return self

    async def get_messages(self, user_id: str, skip: int, limit: int):
        return (
            await self.messages.find({"user_id": user_id})
            .sort("timestamp", -1)
            .skip(skip)
            .limit(limit)
            .to_list(None)
        )

    async def get_recent_messages(self, user_id: str, limit: int = 1) -> List[dict]:
        """Retrieve conversation context from MongoDB"""
        return await mongo_db.db.messages.find(
            {"user_id": user_id}, sort=[("timestamp", -1)], limit=limit
        ).to_list(length=limit)


mongo_db = MongoDB()
