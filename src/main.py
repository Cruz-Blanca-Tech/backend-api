from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer
from src.contexts.security_access.infrastructure.api.middleware.auth_middleware import AuthMiddleware
from src.contexts.security_access.infrastructure.di.security_container import SecurityAccessContainer
from src.core.config import settings
from src.contexts.security_access.presentation.routes import security_app
from src.contexts.document_intake_ocr.presentation.api.routes import intake_app
from src.contexts.data_quality_triage.presentation.api.routes import triage_app
from src.contexts.core_beneficiary_management.presentation.api.routes import beneficiary_app
from src.contexts.reporting_analytics.api.routes import reporting_app

from src.core.events.event_dispatcher import EventDispatcher
from src.contexts.data_quality_triage.domain.shared.events.triage_events import DossierRejectedEvent, BatchRejectedEvent
from src.contexts.shared.events.batch_triage_completed_event import BatchTriageCompletedEvent
from src.contexts.shared.events.dossier_approved_event import DossierApprovedEvent
from src.contexts.shared.events.documents_extracted_event import DocumentsExtractedEvent
from src.contexts.shared.events.batch_ocr_completed_event import BatchOcrCompletedEvent
from src.contexts.document_intake_ocr.application.event_handlers.intake_event_handlers import (
    handle_dossier_approved, handle_dossier_rejected, handle_batch_rejected, handle_batch_triage_completed
)
from src.contexts.data_quality_triage.application.shared.handlers.triage_event_handler import (
    handle_documents_extracted, handle_batch_ocr_completed
)
from fastapi.openapi.utils import get_openapi

from src.core.handlers.exception_handler import configure_exception_handlers

# Aquí tendrías tu instancia de provider (o contenedor)
# 1. Instancias la app
security = HTTPBearer()
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("uvicorn.error")
app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
)
auth_container = SecurityAccessContainer()
app.add_middleware(AuthMiddleware, token_provider=auth_container.token_provider)

@app.on_event("startup")
async def startup_event():
    # Registrar handlers de eventos de dominio
    EventDispatcher.register(DossierApprovedEvent, handle_dossier_approved)
    EventDispatcher.register(DossierRejectedEvent, handle_dossier_rejected)
    EventDispatcher.register(BatchRejectedEvent, handle_batch_rejected)
    EventDispatcher.register(BatchTriageCompletedEvent, handle_batch_triage_completed)
    
    # Evento de OCR (Intake) hacia Triage
    EventDispatcher.register(DocumentsExtractedEvent, handle_documents_extracted)
    EventDispatcher.register(BatchOcrCompletedEvent, handle_batch_ocr_completed)
    
    # Registrar handlers de core_beneficiary_management (MDM)
    from src.contexts.core_beneficiary_management.infrastructure.events.beneficiary_event_handlers import register_beneficiary_event_handlers
    register_beneficiary_event_handlers()
    
    logger.info("Event handlers registrados exitosamente.")

# 2. Registras AuthMiddleware primero (se ejecutará al final, lo cual es correcto)

# 3. Registras CORSMiddleware después (se ejecutará primero, manejando el tráfico CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL,"http://127.0.0.1:8000", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title=app.title,
        version="1.0.0",
        routes=app.routes,
    )
    openapi_schema["components"]["securitySchemes"] = {
        "Bearer Auth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }
    }
    openapi_schema["security"] = [{"Bearer Auth": []}]
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi


configure_exception_handlers(app)          # Para la app raíz
configure_exception_handlers(intake_app)   # Para el contexto de Ingesta
configure_exception_handlers(security_app) # Para el contexto de Seguridad
configure_exception_handlers(triage_app)   # Para el contexto de Triage
configure_exception_handlers(beneficiary_app) # Para el contexto de Beneficiarios
configure_exception_handlers(reporting_app) # Para el contexto de Reporting


# Registrar routers de cada Bounded Context bajo el prefijo común
app.mount(f"{settings.API_V1_STR}/intake", intake_app)
app.mount("/auth", security_app)
app.mount(f"{settings.API_V1_STR}/triage", triage_app)
app.mount(f"{settings.API_V1_STR}/mdm", beneficiary_app)
app.mount(f"{settings.API_V1_STR}/reporting", reporting_app)

@app.get("/", tags=["General"])
async def root():
    return {
        "message": f"Bienvenido a la API de {settings.PROJECT_NAME}",
        "docs": "/docs",
        "status": "active",
    }
