from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings
from app.models.mongo_models import MessageLog


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


mongo_db = MongoDB()
