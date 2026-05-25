from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.core.config import settings
from src.contexts.security_access.api.routes import router as security_router
from src.contexts.document_intake_ocr.api.routes import router as intake_router
from src.contexts.data_quality_triage.api.routes import router as triage_router
from src.contexts.reporting_analytics.api.routes import router as reporting_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configurar middleware CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, configurar dominios específicos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registrar routers de cada Bounded Context bajo el prefijo común
app.include_router(security_router, prefix=settings.API_V1_STR)
app.include_router(intake_router, prefix=settings.API_V1_STR)
app.include_router(triage_router, prefix=settings.API_V1_STR)
app.include_router(reporting_router, prefix=settings.API_V1_STR)

@app.get("/", tags=["General"])
async def root():
    return {
        "message": f"Bienvenido a la API de {settings.PROJECT_NAME}",
        "docs": "/docs",
        "status": "active",
    }
