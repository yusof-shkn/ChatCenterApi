from typing import List
import logging
import uuid
from datetime import datetime
from fastapi import Depends
from app.core.config import settings
from app.models.postgres_models import SessionHistory
from app.models.mongo_models import MessageLog
from app.db.mongodb import mongo_db
from app.core.cache import RedisCacheManager
from .schemas import MessageResponse
from app.core.nlp.services import NLPService
from app.core.nlp.schemas import IntentConfig
from app.dependencies import get_nlp_service, get_redis
from fastapi.encoders import jsonable_encoder

logger = logging.getLogger(__name__)

# Constants
MESSAGE_PROCESSING_ERROR = "Message processing failed"
MESSAGE_RETRIEVAL_ERROR = "Failed to retrieve messages"
CACHE_KEY_TEMPLATE = "messages:{user_id}:{skip}:{limit}"
CACHE_TTL = 60  # seconds


async def store_in_postgres(user_id: uuid.UUID, text: str, result: dict) -> None:
    """Store message in PostgreSQL with error handling"""
    try:
        await SessionHistory.create(
            user_id=user_id,
            message=text,
            response=result["response"],
        )
        logger.info(f"Stored in PostgreSQL: user={user_id}")
    except Exception as e:
        logger.error(f"PostgreSQL storage failed: user={user_id}: {str(e)}")
        raise


async def store_in_mongodb(user_id: uuid.UUID, text: str, result: dict) -> None:
    """Store message in MongoDB with error handling"""
    try:
        message_log = MessageLog(
            user_id=str(user_id),
            text=text,
            intent=result["intent"],
            response=result["response"],
            processed=True,
        )
        await mongo_db.insert_message(message_log)
        logger.info(f"Stored in MongoDB: user={user_id}")
    except Exception as e:
        logger.error(f"MongoDB storage failed: user={user_id}: {str(e)}")
        raise


async def get_all_messages(
    user_id: uuid.UUID,
    skip: int,
    limit: int,
    use_cache: bool,
    redis: RedisCacheManager = Depends(get_redis),
) -> List[MessageResponse]:
    cache_key = CACHE_KEY_TEMPLATE.format(user_id=user_id, skip=skip, limit=limit)

    # Try cache
    if use_cache:
        cached = await redis.get(cache_key)
        if cached:
            return [MessageResponse(**item) for item in cached]

    # Database query
    rows = (
        await SessionHistory.filter(user_id=user_id)
        .order_by("-created_at")
        .offset(skip)
        .limit(limit)
    )

    messages = [
        MessageResponse(
            text=row.message,
            response=row.response,
            timestamp=str(row.created_at),
        )
        for row in rows
    ]

    # Cache with proper serialization
    if use_cache:
        await redis.set(
            cache_key, jsonable_encoder([msg.dict() for msg in messages]), ttl=CACHE_TTL
        )

    return messages


async def process_message(
    text: str,
    redis: RedisCacheManager = Depends(get_redis),
    nlp_service: NLPService = None,
) -> dict:
    """
    Process a message to determine its intent and generate a response.
    Uses NLPService for intent detection and caches results in Redis.

    Args:
        text: Input message text.
        redis: RedisCacheManager instance for caching.
        nlp_service: NLPService instance from app.state.

    Returns:
        Dict with intent, response, and metadata.
    """
    try:
        # Check Redis cache
        cache_key = f"intent:{text.lower()}"
        cached_intent = await redis.get(cache_key)
        if cached_intent:
            config = nlp_service.intent_configs.get(
                cached_intent,
                IntentConfig(
                    patterns=[], responses=["I'm not sure how to respond to that."]
                ),
            )
            return {
                "intent": cached_intent,
                "response": config.responses[0],
                "timestamp": datetime.utcnow(),
            }

        # NLP processing
        intent = nlp_service.determine_intent(text.lower())

        # Cache the result
        await redis.set(cache_key, intent, ttl=CACHE_TTL)

        # Get response from intent_configs
        config = nlp_service.intent_configs.get(
            intent,
            IntentConfig(
                patterns=[], responses=["I'm not sure how to respond to that."]
            ),
        )
        response = config.responses[0]

        return {
            "intent": intent,
            "response": response,
            "timestamp": datetime.utcnow(),
        }

    except Exception as e:
        logger.error(f"Message processing failed: {str(e)}")
        raise RuntimeError(MESSAGE_PROCESSING_ERROR)
