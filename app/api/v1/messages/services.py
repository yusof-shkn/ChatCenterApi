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
from .schemas import MessageResponse, MessageResponsePostgre
from app.core.nlp.services import NLPService
from app.core.nlp.schemas import IntentConfig
from app.dependencies import get_redis
from fastapi.encoders import jsonable_encoder

import json
import random
from app.core.nlp.handlers.weather import WeatherHandler
from app.core.nlp.handlers.support import SupportHandler
from app.core.nlp.handlers.company import CompanyHandler
from app.core.nlp.handlers.social import SocialHandler
from app.core.nlp.handlers import IntentRouter
from app.core.nlp.dependencies import get_intent_router

from app.core.nlp.handlers.weather import WeatherContext
from app.core.nlp.handlers.company import CompanyContext
from app.core.nlp.handlers.support import SupportContext
from app.core.nlp.handlers.social import SocialContext

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
    """Enhanced storage with conversation tracking"""
    try:
        prev = await mongo_db.get_recent_messages({"user_id": str(user_id)}, limit=1)

        message_log = MessageLog(
            user_id=str(user_id),
            text=text,
            intent=result["intent"],
            response=result["response"],
            entities=result.get("entities"),
            processed=True,
            timestamp=result["timestamp"],
            prev_intent=prev["intent"] if prev else None,
            prev_text=prev["text"] if prev else None,
            retry_count=result.get("retry_count", 0),
        )

        await mongo_db.insert_message(message_log)
        logger.info(f"Stored message for {user_id} ({message_log.intent})")

    except Exception as e:
        logger.error(f"MongoDB error: {str(e)}")
        raise


async def get_city_weather(city: str, time: str = "today") -> dict:
    return {
        "description": f"{time} in {city} the weather is fine",
        "temperature": random.randint(20, 30),
    }


async def get_all_messages(
    user_id: uuid.UUID,
    skip: int,
    limit: int,
    use_cache: bool,
    redis: RedisCacheManager = Depends(get_redis),
) -> List[MessageResponsePostgre]:
    cache_key = CACHE_KEY_TEMPLATE.format(user_id=user_id, skip=skip, limit=limit)

    # Try cache
    if use_cache:
        cached = await redis.get(cache_key)
        if cached:
            return [MessageResponsePostgre(**item) for item in cached]

    # Database query
    rows = (
        await SessionHistory.filter(user_id=user_id)
        .order_by("-created_at")
        .offset(skip)
        .limit(limit)
    )

    messages = [
        MessageResponsePostgre(
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
    user_id: uuid.UUID,
    username: str,
    email: str,
    text: str,
    nlp_service: NLPService,
    intent_router: IntentRouter,
) -> dict:
    """
    Process user message through NLP pipeline and intent handlers.
    Returns final response with metadata.
    """
    # Fetch previous conversation context
    prev_docs = await mongo_db.get_recent_messages(str(user_id), limit=1)
    prev_context = prev_docs[0] if prev_docs else {}

    # Get NLP processing result
    nlp_result = nlp_service.process_text(text)

    # Build base context structure
    base_context = {
        "user_id": user_id,
        "user_name": username,
        "email": email,
        "text": text,
        "language": nlp_result.language,
        "current_intent": nlp_result.intent,
        "entities": nlp_result.entities,
        "prev_intent": prev_context.get("intent"),
        "prev_entities": prev_context.get("entities", {}),
        "retry_count": prev_context.get("retry_count", 0),
        "timestamp": datetime.utcnow(),
        "result": {
            "intent": nlp_result.intent,
            "response": nlp_result.response,
            "entities": nlp_result.entities,
            "timestamp": datetime.utcnow().isoformat(),
            "from_cache": False,
        },
    }

    # Get processing order from router
    processing_order = intent_router.get_processing_order()

    # Process through handlers in sequence
    for handler_name in processing_order:
        handler = intent_router.get_handler(handler_name)
        if not handler:
            continue

        # Create appropriate context type
        context = create_handler_context(handler_name, base_context)

        # Skip non-social handlers if social intent detected
        if handler_name != "social" and base_context["result"]["intent"] in [
            "greeting",
            "farewell",
        ]:
            continue

        # Execute handler and update context
        try:
            result = await handler.handle(context)
            base_context.update(
                {
                    "result": result,
                    "current_intent": result["intent"],
                    "entities": result.get("entities", {}),
                }
            )
        except Exception as e:
            logger.error("Handler %s failed: %s", handler_name, str(e))
            continue

    # Persist final result
    final_result = base_context["result"]
    await store_in_mongodb(user_id, text, final_result)

    return final_result


def create_handler_context(handler_name: str, base_context: dict):
    """Factory method for creating typed contexts"""
    context_map = {
        "social": SocialContext,
        "weather": WeatherContext,
        "support": SupportContext,
        "company": CompanyContext,
    }
    return context_map[handler_name](**base_context)
