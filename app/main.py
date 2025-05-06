from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from debug_toolbar.middleware import DebugToolbarMiddleware
from app.api.v1.auth import router as auth
from app.api.v1.messages import router as messages
from app.core.config import settings
from app.core.startup import initialize_application, shutdown_application
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from app.middleware.logging import LoggingMiddleware
from app.middleware.error_handling import ErrorHandlingMiddleware
import uvicorn
from app.middleware.logging import LoggingMiddleware
from app.core.logging import setup_logging
import logging

logger = logging.getLogger("app.main")
# Configure logging first
setup_logging()

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url=None,
)

# Initialize Jinja2 templates
templates = Jinja2Templates(directory="templates")


# Application lifecycle events
@app.on_event("startup")
async def startup_event():
    """Handle application startup"""
    logger.info("Application starting up...")
    await initialize_application(app)


@app.on_event("shutdown")
async def shutdown_event():
    """Handle application shutdown"""
    logger.info("Application shutting down...")
    await shutdown_application(app)


# Middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(LoggingMiddleware)
app.add_middleware(ErrorHandlingMiddleware)

if settings.DEBUG:
    app.add_middleware(DebugToolbarMiddleware)
    logger.info("Debug tools enabled")

# API endpoints
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(messages.router, prefix="/message", tags=["Messages"])


# Static files and templates
@app.get("/", include_in_schema=False)
async def serve_index(request: Request):
    """Serve frontend entry point"""
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "app_name": app.title, "app_version": app.version},
    )


app.mount("/static", StaticFiles(directory="static"), name="static")


# Health endpoint
@app.get("/health", include_in_schema=False)
async def health_check():
    """Service health check"""
    return {"status": "ok", "version": app.version}


# Run the application
if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
