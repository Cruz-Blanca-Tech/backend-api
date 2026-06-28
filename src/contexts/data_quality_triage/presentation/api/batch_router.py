from uuid import UUID
import logging
from fastapi import APIRouter, Depends

from src.contexts.data_quality_triage.application.shared.schemas.triage_schemas import (
    BatchTriageSummary, TriageRejectRequest, PaginatedTriageResponse, TriageCaseListItem
)
from src.contexts.data_quality_triage.infrastructure.dependencies.triage_deps import (
    get_reject_batch_use_case, get_cases_by_batch_use_case,
)
from src.contexts.data_quality_triage.application.shared.use_cases.reject_batch_use_case import RejectBatchUseCase
from src.contexts.data_quality_triage.application.shared.use_cases.get_cases_by_batch_use_case import GetCasesByBatchUseCase

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/batch", tags=["Triage Batches"])

HARDCODED_USER_ID = UUID("00000000-0000-0000-0000-000000000001")



@router.post("/{batch_id}/reject")
async def reject_batch(batch_id: UUID, payload: TriageRejectRequest, reject_uc: RejectBatchUseCase = Depends(get_reject_batch_use_case)):
    """Rechaza masivamente todos los casos pendientes de un lote."""
    rejected_count = await reject_uc.execute(batch_id=batch_id, user_id=HARDCODED_USER_ID, reason=payload.reason)
    return {"batch_id": str(batch_id), "rejected_count": rejected_count, "message": f"{rejected_count} expedientes rechazados"}

@router.get("/{batch_id}/cases", response_model=PaginatedTriageResponse)
async def get_cases_by_batch(
    batch_id: UUID,
    skip: int = 0,
    limit: int = 100,
    use_case: GetCasesByBatchUseCase = Depends(get_cases_by_batch_use_case)
):
    """Devuelve la lista de expedientes de triaje que pertenecen a un lote (batch) específico."""
    return await use_case.execute(batch_id, skip=skip, limit=limit)
