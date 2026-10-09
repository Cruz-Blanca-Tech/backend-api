from typing import Literal, Optional
from pydantic import computed_field, model_validator
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
    DATABASE_URL: Optional[str] = None
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "cruz_blanca"
    FRONTEND_URL: str = "http://localhost:3000"

    @computed_field
    @property
    def ASYNC_DATABASE_URI(self) -> str:
        if self.DATABASE_URL:
            url = self.DATABASE_URL
            if url.startswith("postgresql://"):
                url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
            elif url.startswith("postgres://"):
                url = url.replace("postgres://", "postgresql+asyncpg://", 1)
            return url
            
        # En producción la cadena de conexión SOLO llega por variable de entorno
        # (DATABASE_URL, inyectada como secreto en Azure Container Apps).
        # Nunca se escriben credenciales en el código fuente (ISO/IEC 27001 A.8.24).
        if self.ENVIRONMENT == "production":
            raise RuntimeError(
                "DATABASE_URL no está configurada. En producción debe definirse "
                "como variable de entorno/secreto del contenedor."
            )

        # Fallback para local
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    # Security & Access (OAuth2 & RBAC)
    # Valor solo apto para desarrollo local; en producción se exige uno propio
    # (ver _validar_secretos_produccion más abajo).
    SECRET_KEY: str = "dev-only-insecure-key"
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
    # Modelo por defecto para extracción síncrona. Puede ser un modelo custom
    # entrenado (ej: "nombre-del-modelo") o un prebuilt (ej: "prebuilt-document").
    AZURE_CUSTOM_MODEL_ID: str = "prebuilt-document"

    # Azure OpenAI
    AZURE_OPENAI_ENDPOINT: str = ""
    AZURE_OPENAI_API_KEY: str = ""

    @model_validator(mode="after")
    def _validar_secretos_produccion(self) -> "Settings":
        """Falla al arrancar si producción usa secretos por defecto o débiles."""
        if self.ENVIRONMENT == "production":
            if self.SECRET_KEY == "dev-only-insecure-key" or len(self.SECRET_KEY) < 32:
                raise ValueError(
                    "SECRET_KEY debe definirse por variable de entorno en producción "
                    "(mínimo 32 caracteres aleatorios)."
                )
            if not self.DATABASE_URL:
                raise ValueError("DATABASE_URL es obligatoria en producción.")
        return self

settings = Settings()
