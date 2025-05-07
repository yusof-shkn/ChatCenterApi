from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.core.config import settings
from app.db.postgres import postgres_manager
from app.db.mongodb import mongo_db
from app.core.nlp.services import NLPService
from app.core.cache import RedisCacheManager
import logging
from fastapi_limiter import FastAPILimiter

logger = logging.getLogger("app.core")


async def initialize_application(app: FastAPI) -> None:
    try:
        # PostgreSQL
        await postgres_manager.init()
        logger.info("PostgreSQL connected")

        # MongoDB
        await mongo_db.init_mongo()
        logger.info("MongoDB connected")

        # Redis Cache
        redis_cache = RedisCacheManager()
        app.state.redis_cache = redis_cache
        logger.info("Redis cache initialized")

        # Rate Limiter - Use the raw Redis connection
        await FastAPILimiter.init(redis_cache.raw_redis)
        logger.info("Rate Limiter initialized")

        # NLP Service
        nlp_service = NLPService()
        app.state.nlp_service = nlp_service
        logger.info("NLPService initialized (model: %s)", settings.NLP_MODEL_NAME)

    except Exception as e:
        logger.critical("Application startup failed: %s", str(e), exc_info=True)
        raise


async def shutdown_application(app: FastAPI) -> None:
    """Shut down application and close all connections."""
    try:
        logger.info("Shutting down application connections")

        # Redis Cache
        if hasattr(app.state, "redis_cache"):
            # Flush all keys from the Redis cache
            await app.state.redis_cache.raw_redis.flushdb()
            logger.info("Redis cache flushed")

            # Close the Redis connection
            await app.state.redis_cache.close()
            del app.state.redis_cache
            logger.debug("Redis cache connection closed")

        # PostgreSQL
        if hasattr(app.state, "postgres_manager"):
            await app.state.postgres_manager.close()
            del app.state.postgres_manager
            logger.debug("PostgreSQL connection closed")

        # MongoDB
        await mongo_db.close()
        logger.debug("MongoDB connection closed")

        # NLP Service
        if hasattr(app.state, "nlp_service"):
            del app.state.nlp_service
            logger.debug("NLPService cleaned up")

    except Exception as e:
        logger.warning("Application shutdown error: %s", str(e), exc_info=True)
