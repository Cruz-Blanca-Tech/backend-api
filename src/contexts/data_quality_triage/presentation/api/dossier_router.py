from uuid import UUID
import logging
from fastapi import APIRouter, Depends, Query

from src.contexts.data_quality_triage.application.shared.schemas.triage_schemas import (
    PaginatedTriageResponse
)
from src.contexts.data_quality_triage.infrastructure.dependencies.triage_deps import (
    get_triage_query_service,
)
from src.contexts.data_quality_triage.application.shared.services.triage_query_service import TriageQueryService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/dossier", tags=["Triage Dossiers"])

@router.get("/batch/{batch_id}", response_model=PaginatedTriageResponse)
async def get_triage_inbox_by_batch(
    batch_id: UUID,
    skip: int = Query(0, ge=0), 
    limit: int = Query(20, ge=1, le=100), 
    query_service: TriageQueryService = Depends(get_triage_query_service)
):
    """Bandeja de entrada: Lista todos los expedientes de un lote específico que requieren revisión."""
    return await query_service.get_cases_by_batch(batch_id=batch_id, skip=skip, limit=limit)

@router.post("/manual-trigger", status_code=202)
async def manual_triage_trigger(batch_id: UUID, dni_reference: str, activity_id: UUID):
    """
    Endpoint de rescate/soporte técnico: 
    Dispara manualmente el motor de Triage para un expediente específico simulando la señal del OCR.
    """
    from src.core.events.event_dispatcher import EventDispatcher
    from src.contexts.shared.events.documents_extracted_event import DocumentsExtractedEvent
    
    event = DocumentsExtractedEvent(
        batch_id=batch_id,
        activity_id=activity_id,
        dni_reference=dni_reference
    )
    
    # Lo mandamos al bus para que el background task lo tome.
    await EventDispatcher.dispatch(event)
    
    return {
        "status": "accepted",
        "message": f"Señal de triage enviada manualmente para el DNI {dni_reference} en el lote {batch_id}",
        "action_required": "Revisa la bandeja de entrada (/batch/{batch_id}) en unos segundos"
    }
