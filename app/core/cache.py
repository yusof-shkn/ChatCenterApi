from aiocache import Cache
from aiocache.serializers import JsonSerializer
from app.core.config import settings
from redis.asyncio import Redis


class RedisCacheManager:
    def __init__(self):
        self.cache = Cache(
            Cache.REDIS,
            endpoint=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            namespace=settings.REDIS_NAMESPACE,
            serializer=JsonSerializer(),
            timeout=settings.REDIS_TIMEOUT,
        )
        # Expose raw Redis connection for rate limiter
        self.raw_redis = Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            password=settings.REDIS_PASSWORD,
            decode_responses=True,
        )

    async def get(self, key: str):
        return await self.cache.get(key)

    async def set(self, key: str, value, ttl: int = None):
        return await self.cache.set(key, value, ttl=ttl)

    async def close(self):
        await self.cache.close()
        await self.raw_redis.close()

    async def delete(self, key: str):
        return await self.cache.delete(key)


redis_cache = RedisCacheManager()
