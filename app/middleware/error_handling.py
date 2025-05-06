# app/middleware/errors.py
import logging
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.exceptions import HTTPException

logger = logging.getLogger("app.middleware")


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            return await call_next(request)
        except HTTPException as http_exc:
            logger.warning(
                "HTTP Exception",
                extra={
                    "detail": http_exc.detail,
                    "status_code": http_exc.status_code,
                    "path": request.url.path,
                },
            )
            raise
        except Exception as exc:
            logger.exception(
                "Unhandled exception",
                extra={
                    "path": request.url.path,
                    "method": request.method,
                    "client": request.client.host if request.client else "unknown",
                },
            )
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal Server Error",
                    "message": "An unexpected error occurred",
                },
            )
