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
from .schemas import MessageResponse
from app.dependencies import get_redis, get_current_user
from .services import (
    process_message,
    store_in_postgres,
    store_in_mongodb,
    get_all_messages,
)
import logging
from app.core.nlp.services import NLPService
from app.dependencies import get_nlp_service
from app.core.cache import RedisCacheManager
from app.utils.cache import cache_response
from app.core.config import settings
from fastapi_limiter.depends import RateLimiter
from app.core.nlp.handlers.weather import WeatherHandler
from app.core.nlp.handlers.support import SupportHandler
from app.core.nlp.handlers.comany import CompanyHandler
from app.core.nlp.handlers.social import SocialHandler

from app.core.nlp.dependencies import (
    get_weather_handler,
    get_support_handler,
    get_company_handler,
    get_social_handler,
)

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
    weather_handler: WeatherHandler = Depends(get_weather_handler),
    support_handler: SupportHandler = Depends(get_support_handler),
    company_handler: CompanyHandler = Depends(get_company_handler),
    social_handler: SocialHandler = Depends(get_social_handler),
):
    logger.info("send_message called by user=%s with text=%r", user.id, text)
    try:
        result = await process_message(
            user_id=user.id,
            username=user.username,
            email=user.email,
            text=text,
            nlp_service=nlp_service,
            weather_handler=weather_handler,
            support_handler=support_handler,
            company_handler=company_handler,
            social_handler=social_handler,
        )
    except RuntimeError as err:
        logger.exception("send_message: processing failed for user=%s", user.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while processing your message.",
        )

    logger.info(
        "send_message succeeded for user=%s: intent=%s response=%r",
        user.id,
        result["intent"],
        result["response"],
    )

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
    response_model=List[MessageResponse],
    dependencies=[Depends(RateLimiter(times=100, seconds=60))],
)
@cache_response()
async def get_messages(
    user=Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, le=100),
    use_cache: bool = True,
    redis: RedisCacheManager = Depends(get_redis),
) -> List[MessageResponse]:
    return await get_all_messages(user.id, skip, limit, use_cache, redis)
