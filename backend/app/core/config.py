"""
DPDP GUI Compliance Scanner - Configuration Settings
"""
from functools import lru_cache
from typing import List, Optional, Union

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    APP_NAME: str = "DPDP GUI Compliance Scanner"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"

    # API
    API_V1_PREFIX: str = "/api/v1"

    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480  # 8 hours - token lifetime
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30  # 30 days for refresh token
    ALGORITHM: str = "HS256"

    # Session Inactivity Settings
    SESSION_INACTIVITY_TIMEOUT_MINUTES: int = 5  # Logout after 5 min of inactivity
    HEARTBEAT_INTERVAL_SECONDS: int = 30  # Frontend sends heartbeat every 30 sec

    # CORS - accepts comma-separated string or list
    CORS_ORIGINS: Union[List[str], str] = ["http://localhost:3000", "http://localhost:5173"]

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/dpdp_scanner"
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # MinIO (Object Storage)
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET_NAME: str = "dpdp-evidence"
    MINIO_SECURE: bool = False

    # Scanning Configuration
    MAX_CRAWL_PAGES: int = 100
    SCAN_TIMEOUT_SECONDS: int = 1800  # 30 minutes
    SCREENSHOT_QUALITY: int = 80
    MAX_CONCURRENT_SCANS: int = 10

    # NLP Configuration
    SPACY_MODEL_EN: str = "en_core_web_sm"
    SPACY_MODEL_HI: str = "xx_ent_wiki_sm"  # Multilingual model
    MIN_READABILITY_SCORE: float = 60.0

    # Playwright Configuration
    BROWSER_HEADLESS: bool = True
    BROWSER_TIMEOUT_MS: int = 30000
    PAGE_LOAD_WAIT_MS: int = 5000

    # Windows Scanner Configuration
    TESSERACT_CMD: Optional[str] = None  # Path to tesseract executable

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            # Handle JSON array format or comma-separated
            if v.startswith("["):
                import json
                try:
                    return json.loads(v)
                except json.JSONDecodeError:
                    pass
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v if v else []


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
