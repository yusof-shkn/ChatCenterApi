import logging
from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware


def 
etup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


async def log_requests(request: Request, call_next):
    logger = logging.getLogger("request")
    logger.info(f"Request: {request.method} {request.url}")
    response = await call_next(request)
    return response
