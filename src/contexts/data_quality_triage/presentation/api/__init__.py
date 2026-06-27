from fastapi import APIRouter

from src.contexts.data_quality_triage.presentation.api.batch_router import router as batch_router
from src.contexts.data_quality_triage.presentation.api.dossier_router import router as dossier_router
from src.contexts.data_quality_triage.presentation.api.educa_router import router as educa_router

triage_api_router = APIRouter()

# Health check simple del contexto
@triage_api_router.get("/health", tags=["Data Quality & Triage"])
async def health_check():
    return {"status": "ok", "context": "Data Quality & Triage"}

# Incluimos los módulos separados
triage_api_router.include_router(batch_router)
triage_api_router.include_router(dossier_router)
triage_api_router.include_router(educa_router)
