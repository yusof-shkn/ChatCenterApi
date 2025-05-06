from app.core.config import settings

TORTOISE_ORM = {
    "connections": {"default": settings.POSTGRES_URL},
    "apps": {
        "models": {
            "models": ["app.models.postgres_models", "aerich.models"],
            "default_connection": "default",
        }
    },
}
