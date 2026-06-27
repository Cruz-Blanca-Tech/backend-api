from uuid import UUID
import logging
from fastapi import APIRouter, Depends

from src.contexts.data_quality_triage.application.shared.schemas.triage_schemas import (
    BatchProcessingResult, BatchTriageSummary, TriageRejectRequest, PaginatedTriageResponse, TriageCaseListItem
)
from src.contexts.data_quality_triage.infrastructure.dependencies.triage_deps import (
    get_dossier_processor, get_triage_correction_service, get_triage_query_service,
)
from src.contexts.data_quality_triage.application.shared.services.dossier_processor import DossierProcessor
from src.contexts.data_quality_triage.application.shared.services.triage_correction_service import TriageCorrectionService
from src.contexts.data_quality_triage.application.shared.services.triage_query_service import TriageQueryService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/batch", tags=["Triage Batches"])

HARDCODED_USER_ID = UUID("00000000-0000-0000-0000-000000000001")

@router.post("/process/{batch_id}", response_model=BatchProcessingResult)
async def process_batch(batch_id: UUID, processor: DossierProcessor = Depends(get_dossier_processor)):
    """Inicia el procesamiento masivo de un lote desde Ingesta."""
    return await processor.process_batch(batch_id)

@router.get("/{batch_id}/summary", response_model=BatchTriageSummary)
async def get_batch_summary(batch_id: UUID, query_service: TriageQueryService = Depends(get_triage_query_service)):
    """Obtiene un resumen estadístico de los estados de los casos de un lote."""
    return await query_service.get_batch_summary(batch_id)

@router.post("/{batch_id}/reject")
async def reject_batch(batch_id: UUID, payload: TriageRejectRequest, correction_service: TriageCorrectionService = Depends(get_triage_correction_service)):
    """Rechaza masivamente todos los casos pendientes de un lote."""
    rejected_count = await correction_service.reject_batch(batch_id=batch_id, user_id=HARDCODED_USER_ID, reason=payload.reason)
    return {"batch_id": str(batch_id), "rejected_count": rejected_count, "message": f"{rejected_count} expedientes rechazados"}

@router.get("/{batch_id}/cases", response_model=PaginatedTriageResponse)
async def get_cases_by_batch(
    batch_id: UUID,
    skip: int = 0,
    limit: int = 100,
    query_service: TriageQueryService = Depends(get_triage_query_service)
):
    """Devuelve la lista de expedientes de triaje que pertenecen a un lote (batch) específico."""
    # We will use the existing get_triage_inbox but filter by batch if added to the query service,
    # or add a new method. For now we will call a new method `get_cases_by_batch`
    return await query_service.get_cases_by_batch(batch_id, skip=skip, limit=limit)
