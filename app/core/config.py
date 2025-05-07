from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import RedisDsn, PostgresDsn, computed_field
from pathlib import Path
from typing import Dict, Any, List


class CacheConfig:
    def __init__(self, namespace: str):
        self.KEY_PREFIX = f"{namespace}:"
        self.SESSION_KEY_PREFIX = "session:"
        self.USER_KEY = "users"
        self.SESSION_TTL = 3600  # 1 hour
        self.USER_TTL = 300  # 5 minutes


class Settings(BaseSettings):
    # --------------------------
    # Application Core Settings
    # --------------------------
    APP_NAME: str = "Chat Center API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    MAINTENANCE_MODE: bool = False
    ADMIN_EMAIL: str = "admin@example.com"

    # --------------------------
    # Security & Authentication
    # --------------------------
    SECRET_KEY: str = "your-secret-key-please-change-this"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    HASH_ALGORITHM: str = "bcrypt"
    HASH_ITERATIONS: int = 12

    # --------------------------
    # Database Configuration
    # --------------------------
    # POSTGRES_URL: PostgresDsn = "postgresql://user:pass@localhost/chat_center"
    POSTGRES_URL: str = "postgres://user:pass@localhost/chat_center"
    MONGODB_URL: str = "mongodb://localhost:27017"
    MONGODB_NAME: str = "chat_center"
    MONGODB_MESSAGES_COLLECTION: str = "messages"

    # --------------------------
    # Redis Configuration
    # --------------------------
    REDIS_URL: RedisDsn = "redis://localhost:6379/0"
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""
    REDIS_DB: int = 0
    REDIS_NAMESPACE: str = "chatcenter"
    REDIS_TIMEOUT: int = 5  # Connection timeout in seconds
    REDIS_POOL_MIN: int = 5  # Minimum connections in pool
    REDIS_POOL_MAX: int = 20  # Maximum connections in pool
    DEFAULT_CACHE_TTL: int = 300  # 5 minutes

    # --------------------------
    # Rate Limiting
    # --------------------------
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_PER_MINUTE: int = 100
    RATE_LIMIT_BURST: int = 50  # Maximum burst requests
    RATE_LIMIT_STRATEGY: str = "fixed-window"  # or "token-bucket"

    # --------------------------
    # NLP Configuration
    # --------------------------
    MAX_CONTEXT_LENGTH: int = 1000  # Truncate context after 1000 chars
    CONVERSATION_TIMEOUT: int = 1800  # 30 minutes in seconds
    DEFAULT_LANGUAGE: str = "english"
    DEFAULT_LANGUAGE_CODE: str = "en"
    NLP_MODEL_NAME: str = "en_core_web_md"
    NLP_MODEL_PATH: str = ""  # For custom model loading
    NLP_RESPONSES: Dict[str, str] = {
        "greeting": "Hello! How can I assist you today?",
        "farewell": "Goodbye! Have a great day!",
        "weather": "I recommend checking a weather service for current conditions.",
        "company": "We specialize in AI-powered solutions.",
        "unclear": "Could you please rephrase your question?",
    }
    NLP_CONFIDENCE_THRESHOLD: float = 0.65

    # --------------------------
    # CORS & Security Headers
    # --------------------------
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"
    TRUSTED_HOSTS: str = "localhost,127.0.0.1"
    SECURE_COOKIES: bool = True
    CSRF_PROTECTION: bool = True

    # --------------------------
    # Paths & Directories
    # --------------------------
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    LOGS_DIR: Path = BASE_DIR / "logs"
    STATIC_DIR: Path = BASE_DIR / "static"
    TEMPLATES_DIR: Path = BASE_DIR / "templates"

    # --------------------------
    # API Documentation
    # --------------------------
    DOCS_URL: str = "/docs"
    REDOC_URL: str = "/redoc"
    OPENAPI_URL: str = "/openapi.json"

    # --------------------------
    # Monitoring & Observability
    # --------------------------
    SENTRY_DSN: str = ""
    PROMETHEUS_ENABLED: bool = False
    HEALTH_CHECK_INTERVAL: int = 300  # 5 minutes

    # --------------------------
    # File Uploads
    # --------------------------
    MAX_UPLOAD_SIZE: int = 10  # MB
    ALLOWED_FILE_TYPES: List[str] = ["image/jpeg", "image/png", "application/pdf"]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        env_nested_delimiter="__",
        extra="ignore",
        protected_namespaces=("model_config",),
    )

    @computed_field
    @property
    def cors_origins_list(self) -> List[str]:
        return [
            origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()
        ]

    @computed_field
    @property
    def trusted_hosts_list(self) -> List[str]:
        return [host.strip() for host in self.TRUSTED_HOSTS.split(",") if host.strip()]

    @computed_field
    @property
    def file_upload_limit(self) -> int:
        return self.MAX_UPLOAD_SIZE * 1024 * 1024  # Convert MB to bytes

    @property
    def cache(self) -> CacheConfig:
        return CacheConfig(self.REDIS_NAMESPACE)


settings = Settings()
