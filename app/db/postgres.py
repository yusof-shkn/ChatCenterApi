from tortoise import Tortoise
from app.core.config import settings
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class PostgresManager:
    """
    Manages PostgreSQL connections and schema generation using Tortoise ORM.
    Supports Aerich migrations and integrates with FastAPI application lifecycle.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.tortoise_orm: Dict[str, Any] = {
            "connections": {"default": settings.POSTGRES_URL},
            "apps": {
                "models": {
                    "models": ["app.models.postgres_models", "aerich.models"],
                    "default_connection": "default",
                }
            },
        }
        self.initialized = False

    async def init(self) -> None:
        """
        Initialize PostgreSQL connection with Tortoise ORM and generate schemas.
        Includes Aerich models for migration support.
        """
        if self.initialized:
            self.logger.warning("PostgresManager already initialized, skipping")
            return

        try:
            await Tortoise.init(config=self.tortoise_orm)
            await Tortoise.generate_schemas()
            self.initialized = True
            self.logger.info("PostgreSQL connection initialized and schemas generated")
        except Exception as e:
            self.logger.error(f"Failed to initialize PostgreSQL: {e}")
            raise

    async def close(self) -> None:
        """
        Close PostgreSQL connections managed by Tortoise ORM.
        """
        if not self.initialized:
            self.logger.warning(
                "PostgresManager not initialized, no connections to close"
            )
            return

        try:
            await Tortoise.close_connections()
            self.initialized = False
            self.logger.info("PostgreSQL connections closed")
        except Exception as e:
            self.logger.warning(f"Failed to close PostgreSQL connections: {e}")


postgres_manager = PostgresManager()
