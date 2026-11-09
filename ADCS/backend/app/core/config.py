from pathlib import Path
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL
from typing import List


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    APP_NAME: str = "AI-Driven Academic Compliance System (ADCS)"
    APP_ENV: str = "development"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"

    # Security
    SECRET_KEY: str = "change-me-in-production-use-a-long-random-string"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = 30
    EMAIL_OTP_EXPIRE_MINUTES: int = 10
    FRONTEND_BASE_URL: str = "http://localhost:4173"
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = ""
    DOCUMENT_STORAGE_PATH: Path = Path(__file__).resolve().parents[2] / "private_uploads"
    MAX_DOCUMENT_SIZE_BYTES: int = 10 * 1024 * 1024
    SEED_DEMO_DATA: bool = False

    # Database
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_USER: str
    DB_PASSWORD: str
    DB_NAME: str
    DB_ECHO: bool = False
    DB_SSL: bool = False
    DB_SSL_CA: str = ""

    @property
    def DATABASE_URL(self) -> URL:
        return URL.create(
            drivername="mysql+pymysql",
            username=self.DB_USER,
            password=self.DB_PASSWORD,
            host=self.DB_HOST,
            port=self.DB_PORT,
            database=self.DB_NAME,
            query={"charset": "utf8mb4"},
        )

    # CORS
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    # Email / SMTP
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = "noreply@adcs.local"
    SMTP_FROM_NAME: str = "ADCS"
    SMTP_TLS: bool = True

    # Rate limiting
    RATE_LIMIT_LOGIN: str = "5/minute"
    RATE_LIMIT_REGISTER: str = "3/minute"
    RATE_LIMIT_ACCOUNT_STATUS: str = "10/minute"

    # Risk thresholds (defaults, overridable per institution)
    DEFAULT_ATTENDANCE_THRESHOLD: float = 75.0
    DEFAULT_MISSED_ASSESSMENTS_THRESHOLD: int = 2

    # Super admin seed
    SUPER_ADMIN_EMAIL: str = ""
    SUPER_ADMIN_PASSWORD: str = ""
    SUPER_ADMIN_FULL_NAME: str = "Platform Super Administrator"
    @model_validator(mode="after")
    def validate_production_security(self):
        if self.APP_ENV.lower() in {"prod", "production"}:
            if self.DEBUG:
                raise ValueError("DEBUG must be false in production")
            if len(self.SECRET_KEY) < 32 or self.SECRET_KEY.lower().startswith(("change-me", "replace-with")):
                raise ValueError("Production SECRET_KEY must be a unique secret of at least 32 characters")
        return self


settings = Settings()
