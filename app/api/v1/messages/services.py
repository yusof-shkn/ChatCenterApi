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
import json
import random
from app.core.nlp.handlers.weather import WeatherHandler
from app.core.nlp.handlers.support import SupportHandler
from app.core.nlp.handlers.comany import CompanyHandler
from app.core.nlp.handlers.social import SocialHandler

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
    user_id: uuid.UUID,
    username: str,
    email: str,
    text: str,
    nlp_service: NLPService = Depends(get_nlp_service),
    weather_handler: WeatherHandler = None,
    support_handler: SupportHandler = None,
    company_handler: CompanyHandler = None,
    social_handler: SocialHandler = None,
) -> dict:
    # Fetch previous context
    prev_docs = await mongo_db.get_recent_messages(str(user_id), limit=1)
    prev_intent = prev_docs[0]["intent"] if prev_docs else None
    prev_entities = prev_docs[0].get("entities", {}) if prev_docs else {}
    retry_count = prev_docs[0].get("retry_count", 0) if prev_docs else 0

    # NLP Processing (assuming determine_intent returns language)
    intent, response, entities, language = nlp_service.determine_intent(text)
    result = {
        "intent": intent,
        "response": response,
        "entities": entities,
        "timestamp": datetime.utcnow().isoformat(),
        "from_cache": False,
        "retry_count": 0,
    }

    # Intent Handling with language passed
    result = await social_handler.handle(
        language=language,
        user_name=username,
        email=email,
        text=text,
        current_intent=intent,
        entities=entities,
        prev_intent=prev_intent,
        prev_entities=prev_entities,
        retry_count=retry_count,
        result=result,
    )

    if result["intent"] not in ["greeting", "farewell"]:
        result = await weather_handler.handle(
            language=language,
            text=text,
            current_intent=intent,
            entities=entities,
            prev_intent=prev_intent,
            prev_entities=prev_entities,
            retry_count=retry_count,
            result=result,
        )
        result = await support_handler.handle(
            language=language,
            text=text,
            current_intent=intent,
            entities=entities,
            prev_intent=prev_intent,
            prev_entities=prev_entities,
            retry_count=retry_count,
            result=result,
        )
        result = await company_handler.handle(
            language=language,
            text=text,
            current_intent=intent,
            entities=entities,
            prev_intent=prev_intent,
            prev_entities=prev_entities,
            retry_count=retry_count,
            result=result,
        )

    await store_in_mongodb(user_id, text, result)
    return result
