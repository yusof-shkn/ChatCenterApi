from fastapi import (
    APIRouter,
    Depends,
    Request,
    BackgroundTasks,
    Query,
    HTTPException,
    status,
    Response,
)
from typing import List
from .schemas import MessageResponse,MessageResponsePostgre
from app.dependencies import get_redis, get_current_user
from .services import (
    process_message,
    store_in_postgres,
    store_in_mongodb,
    get_all_messages,
)
import logging
from app.core.nlp.services import NLPService
from app.core.nlp.dependencies import get_nlp_service
from app.core.cache import RedisCacheManager
from app.utils.cache import cache_response
from app.core.config import settings
from fastapi_limiter.depends import RateLimiter
from app.core.nlp.handlers import IntentRouter
from app.core.nlp.dependencies import get_intent_router

router = APIRouter(tags=["Messages"])
logger = logging.getLogger(__name__)


@router.post(
    "/send",
    response_model=MessageResponse,
    dependencies=[Depends(RateLimiter(times=5, seconds=60))],
)
async def send_message(
    text: str,
    user=Depends(get_current_user),
    nlp_service: NLPService = Depends(get_nlp_service),
    intent_router: IntentRouter = Depends(get_intent_router),
):
    logger.info("send_message called by user=%s with text=%r", user.id, text)
    try:
        result = await process_message(
            user_id=user.id,
            username=user.username,
            email=user.email,
            text=text,
            nlp_service=nlp_service,
            intent_router=intent_router,
        )
    except RuntimeError as err:
        logger.exception("Processing failed for user=%s", user.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Message processing failed",
        )

    logger.info("Processed message for user=%s: %s", user.id, result["intent"])

    await store_in_postgres(user.id, text, result)
    await store_in_mongodb(user.id, text, result)

    return MessageResponse(
        text=text,
        intent=result["intent"],
        response=result["response"],
        timestamp=result["timestamp"],
    )


@router.get(
    "/messages",
    response_model=List[MessageResponsePostgre],
    dependencies=[Depends(RateLimiter(times=100, seconds=60))],
)
@cache_response()
async def get_messages(
    user=Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, le=100),
    use_cache: bool = True,
    redis: RedisCacheManager = Depends(get_redis),
) -> List[MessageResponsePostgre]:
    return await get_all_messages(user.id, skip, limit, use_cache, redis)
