# app/middleware/logging.py
import time
import logging
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("app.middleware.logging")


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.time()
        logger.info(f"→ {request.method} {request.url.path} started")
        response = await call_next(request)
        elapsed = (time.time() - start) * 1000
        logger.info(
            f"← {request.method} {request.url.path} completed in {elapsed:.2f}ms "
            f"status_code={response.status_code}"
        )  # turn0search6
        return response
