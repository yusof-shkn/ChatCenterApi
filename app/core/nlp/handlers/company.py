from dataclasses import dataclass
from typing import Dict, Any
from random import choice
import logging
from app.core.nlp.language.manager import LanguageManager
from app.core.nlp.contexts import CompanyContext

logger = logging.getLogger(__name__)


class CompanyHandler:
    """Handles company-related inquiries with dynamic information retrieval"""

    def __init__(self, language_manager: LanguageManager):
        self.lm = language_manager
        logger.info("Initialized CompanyHandler with LanguageManager")

    async def handle(self, context: CompanyContext) -> Dict[str, Any]:
        """Main entry point for company intent processing"""
        logger.debug(
            "Handling company context: text=%s, language=%s, current_intent=%s, entities=%s",
            context.text,
            context.language,
            context.current_intent,
            context.entities,
        )
        try:
            if not self._should_handle(context):
                logger.debug("CompanyHandler not handling context")
                return context.result

            if context.entities.get("specific_info") in [
                "services",
                "history",
                "mission",
                "employees",
                "location",
            ]:
                logger.info(
                    "Processing detailed company request: specific_info=%s",
                    context.entities.get("specific_info"),
                )
                result = await self._handle_detailed_request(context)
            else:
                logger.info("Processing general company request")
                result = await self._handle_general_request(context)

            logger.info(
                "Company request processed: intent=%s, response=%s",
                result.get("intent", "unknown"),
                result.get("response", "none"),
            )
            return result

        except Exception as e:
            logger.error("Company handling failed: %s", str(e))
            error_response = self._create_error_response(context)
            logger.info(
                "Returning error response: intent=%s, response=%s",
                error_response.get("intent", "unknown"),
                error_response.get("response", "none"),
            )
            return error_response

    def _should_handle(self, context: CompanyContext) -> bool:
        """Determine if company handler should process this request"""
        should_handle = context.current_intent == "company"
        logger.debug(
            "Checking if should handle: current_intent=%s, should_handle=%s",
            context.current_intent,
            should_handle,
        )
        return should_handle

    async def _handle_general_request(self, context: CompanyContext) -> Dict[str, Any]:
        """Handle general company information request with fallback safety"""
        lang = self.lm.normalize_language(context.language)
        logger.debug("Normalized language: %s", lang)
        config = self.lm.get_intent_config("company", lang)
        logger.debug("Retrieved config for company intent: %s", config)

        responses = config.get("responses", [])
        if (
            not responses
            or not isinstance(responses, list)
            or not all(isinstance(r, str) for r in responses)
        ):
            logger.warning(
                "Invalid or missing responses in config for company intent, language=%s",
                lang,
            )
            responses = config.get("fallback", "Unknown company information.")
            if isinstance(responses, str):
                responses = [responses]

        response = choice(responses)
        logger.info("Selected general response: %s", response)
        return {**context.result, "intent": "company", "response": response}

    async def _handle_detailed_request(self, context: CompanyContext) -> Dict[str, Any]:
        """Process request for specific company information"""
        info_type = context.entities.get("specific_info", "")
        logger.debug("Handling detailed request for info_type=%s", info_type)
        handler_map = {
            "services": self._handle_services,
            "history": self._handle_history,
            "mission": self._handle_mission,
            "employees": self._handle_employees,
            "location": self._handle_location,
        }

        handler = handler_map.get(info_type, self._handle_unknown_info)
        logger.debug("Selected handler: %s", handler.__name__)
        return await handler(context)

    async def _handle_services(self, context: CompanyContext) -> Dict[str, Any]:
        """Provide detailed service information with validation"""
        lang = self.lm.normalize_language(context.language)
        logger.debug("Handling services request for language: %s", lang)
        config = self.lm.get_intent_config("company", lang)
        logger.debug("Retrieved config for company intent: %s", config)

        services = config.get("services", [])
        if (
            not services
            or not isinstance(services, list)
            or not all(isinstance(s, str) for s in services)
        ):
            logger.warning(
                "Invalid or missing services in config for company intent, language=%s",
                lang,
            )
            services = config.get("fallback", "Unknown services information.")
            if isinstance(services, str):
                services = [services]

        response = choice(services)
        logger.info("Selected services response: %s", response)
        return {
            **context.result,
            "intent": "company_services",
            "response": response,
        }

    async def _handle_history(self, context: CompanyContext) -> Dict[str, Any]:
        """Provide company historical information"""
        lang = self.lm.normalize_language(context.language)
        logger.debug("Handling history request for language: %s", lang)
        config = self.lm.get_intent_config("company", lang)
        logger.debug("Retrieved config for company intent: %s", config)

        history = config.get("company_facts", {}).get("history")
        if not history:
            logger.warning(
                "No history found in config for company intent, language=%s", lang
            )
            history = config.get("fallback", "Unknown history information.")

        logger.info("Selected history response: %s", history)
        return {**context.result, "intent": "company_history", "response": history}

    async def _handle_mission(self, context: CompanyContext) -> Dict[str, Any]:
        """Provide company mission statement"""
        lang = self.lm.normalize_language(context.language)
        logger.debug("Handling mission request for language: %s", lang)
        config = self.lm.get_intent_config("company", lang)
        logger.debug("Retrieved config for company intent: %s", config)

        mission = config.get("company_facts", {}).get("mission")
        if not mission:
            logger.warning(
                "No mission found in config for company intent, language=%s", lang
            )
            mission = config.get("fallback", "Unknown mission information.")

        logger.info("Selected mission response: %s", mission)
        return {**context.result, "intent": "company_mission", "response": mission}

    async def _handle_employees(self, context: CompanyContext) -> Dict[str, Any]:
        """Provide company employee information"""
        lang = self.lm.normalize_language(context.language)
        logger.debug("Handling employees request for language: %s", lang)
        config = self.lm.get_intent_config("company", lang)
        logger.debug("Retrieved config for company intent: %s", config)

        employees = config.get("company_facts", {}).get("employees")
        if not employees:
            logger.warning(
                "No employees info found in config for company intent, language=%s",
                lang,
            )
            employees = config.get("fallback", "Unknown employee information.")

        logger.info("Selected employees response: %s", employees)
        return {**context.result, "intent": "company_employees", "response": employees}

    async def _handle_location(self, context: CompanyContext) -> Dict[str, Any]:
        """Provide company location information"""
        lang = self.lm.normalize_language(context.language)
        logger.debug("Handling location request for language: %s", lang)
        config = self.lm.get_intent_config("company", lang)
        logger.debug("Retrieved config for company intent: %s", config)

        location = config.get("company_facts", {}).get("location")
        if not location:
            logger.warning(
                "No location found in config for company intent, language=%s", lang
            )
            location = config.get("fallback", "Unknown location information.")

        logger.info("Selected location response: %s", location)
        return {**context.result, "intent": "company_location", "response": location}

    async def _handle_unknown_info(self, context: CompanyContext) -> Dict[str, Any]:
        """Handle unrecognized information requests"""
        lang = self.lm.normalize_language(context.language)
        logger.debug("Handling unknown info request for language: %s", lang)
        config = self.lm.get_intent_config("company", lang)
        response = config.get("fallback", "Unknown information.")

        logger.info("Selected unknown info response: %s", response)
        return {**context.result, "intent": "company", "response": response}

    def _create_error_response(self, context: CompanyContext) -> Dict[str, Any]:
        """Create error response for company inquiries"""
        lang = self.lm.normalize_language(context.language)
        logger.debug("Creating error response for language: %s", lang)
        config = self.lm.get_intent_config("company", lang)
        error_msg = config.get("fallback", "Unknown error occurred.")

        logger.info("Selected error response: %s", error_msg)
        return {**context.result, "intent": "company_error", "response": error_msg}
