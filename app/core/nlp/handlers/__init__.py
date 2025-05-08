# app/core/nlp/handlers/__init__.py
import logging
from typing import Dict, Any
from app.core.nlp.language.manager import LanguageManager
from .weather import WeatherHandler
from .support import SupportHandler
from .company import CompanyHandler
from .social import SocialHandler

logger = logging.getLogger(__name__)


class IntentRouter:
    """Central coordinator for intent handling with dependency management"""

    def __init__(self, language_manager: LanguageManager):
        self.language_manager = language_manager
        self._handlers: Dict[str, Any] = {}
        self._initialize_core_handlers()
        logger.info("Intent router initialized with %d handlers", len(self._handlers))

    def _initialize_core_handlers(self):
        """Register default handlers with shared dependencies"""
        self.register_handler("weather", WeatherHandler(self.language_manager))
        self.register_handler("support", SupportHandler(self.language_manager))
        self.register_handler("company", CompanyHandler(self.language_manager))
        self.register_handler("social", SocialHandler(self.language_manager))

    def register_handler(self, intent_type: str, handler: Any):
        """Add or replace a handler for specific intent type"""
        self._handlers[intent_type] = handler
        logger.debug("Registered handler for '%s' intent", intent_type)

    def get_handler(self, intent_type: str) -> Any:
        """Retrieve handler for specified intent type"""
        handler = self._handlers.get(intent_type)
        if not handler:
            logger.warning("No handler registered for intent type '%s'", intent_type)
        return handler

    def get_processing_order(self) -> list:
        """Define default processing sequence"""
        return ["social", "weather", "support", "company"]

    @property
    def available_handlers(self) -> list:
        """Get list of registered handler names"""
        return list(self._handlers.keys())
