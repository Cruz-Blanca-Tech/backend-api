from typing import Literal
from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    # API Configuration
    PROJECT_NAME: str = "Cruz Blanca - Gestión Documental Inteligente"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: Literal["development", "production", "testing"] = "development"

    # Database Configuration
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "cruz_blanca"
    FRONTEND_URL: str = "http://localhost:3000"
    @computed_field
    @property
    def ASYNC_DATABASE_URI(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    # Security & Access (OAuth2 & RBAC)
    SECRET_KEY: str = "super-secret-key-change-in-production-1234567890"  # Cambiar en producción
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 días
    
    # OAuth Google (Security & Access)
    GOOGLE_CLIENT_ID: str =""
    GOOGLE_CLIENT_SECRET: str=""
    GOOGLE_DRIVE_TEMPORARY_CUSTODY_ID: str=""
    GOOGLE_DRIVE_CONSOLIDATED_DOSSIERS_ID: str=""

    ALLOWED_DOMAIN: str ="cruz-blanca.org"

    # Document Intake & OCR (Azure Document Intelligence)
    AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT: str = ""
    AZURE_DOCUMENT_INTELLIGENCE_KEY: str = ""


settings = Settings()
