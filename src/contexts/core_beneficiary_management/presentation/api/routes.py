from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.core.config import settings

from .beneficiary_router import router as beneficiary_router

beneficiary_app = FastAPI(
    title=f"{settings.PROJECT_NAME} - Beneficiary Management",
    openapi_url="/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Apply CORS (usually handled by the main app, but safe to include for modularity)
beneficiary_app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL, "http://127.0.0.1:8000", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

beneficiary_app.include_router(beneficiary_router)
