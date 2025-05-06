import logging
import sys
from logging import Formatter, StreamHandler
from typing import Dict, Any
from app.core.config import settings


class ColorFormatter(Formatter):
    """Logging formatter with ANSI color codes"""

    COLORS = {
        "INFO": "\033[94m",  # Blue
        "WARNING": "\033[93m",  # Yellow
        "ERROR": "\033[91m",  # Red
        "CRITICAL": "\033[91m",  # Red
        "DEBUG": "\033[37m",  # Grey
        "RESET": "\033[0m",
    }

    FORMAT = "%(asctime)s | %(levelname)7s | %(name)s | %(message)s"
    DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

    def format(self, record: logging.LogRecord) -> str:
        # Format the log record without colors first
        formatter = Formatter(self.FORMAT, self.DATE_FORMAT)
        message = formatter.format(record)

        # Apply color to the levelname while preserving alignment
        levelname = record.levelname.ljust(7)
        color = self.COLORS.get(record.levelname, self.COLORS["RESET"])
        return message.replace(levelname, f"{color}{levelname}{self.COLORS['RESET']}")


def setup_logging():
    """Configure colorized logging with proper level formatting"""
    import colorama

    colorama.init(autoreset=True)
    handler = StreamHandler(sys.stdout)
    handler.setFormatter(ColorFormatter())

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.handlers = [handler]
    root_logger.setLevel(logging.DEBUG if settings.DEBUG else logging.INFO)

    # Configure application logger
    app_logger = logging.getLogger("app")
    app_logger.propagate = False
    app_logger.handlers = [handler]

    # Configure third-party loggers
    for name in ["uvicorn", "uvicorn.error", "uvicorn.access"]:
        logging.getLogger(name).handlers = [handler]
        logging.getLogger(name).propagate = False

    # Set higher levels for noisy libraries
    logging.getLogger("pymongo").setLevel(logging.WARNING)
    logging.getLogger("redis").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
