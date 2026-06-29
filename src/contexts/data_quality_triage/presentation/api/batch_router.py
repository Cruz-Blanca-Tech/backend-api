from uuid import UUID
import logging
from fastapi import APIRouter, Depends, HTTPException, status

from src.contexts.data_quality_triage.application.shared.schemas.triage_schemas import (
    BatchTriageSummary, TriageRejectRequest, PaginatedTriageResponse, TriageCaseListItem
)
from src.contexts.data_quality_triage.domain.shared.value_objects.triage_status import TriageStatus, TriageVerdict
from src.contexts.data_quality_triage.infrastructure.dependencies.triage_deps import (
    get_reject_batch_use_case, get_cases_by_batch_use_case, get_verify_batch_completion_use_case, get_batch_summary_use_case
)
from src.contexts.data_quality_triage.application.shared.use_cases.reject_batch_use_case import RejectBatchUseCase
from src.contexts.data_quality_triage.application.shared.use_cases.get_cases_by_batch_use_case import GetCasesByBatchUseCase
from src.contexts.data_quality_triage.application.use_cases.verify_batch_completion_use_case import VerifyBatchCompletionUseCase
from src.contexts.data_quality_triage.application.use_cases.get_batch_summary_use_case import GetBatchSummaryUseCase

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/batch", tags=["Triage Batches"])

HARDCODED_USER_ID = UUID("00000000-0000-0000-0000-000000000001")



@router.post("/{batch_id}/reject")
async def reject_batch(batch_id: UUID, payload: TriageRejectRequest, reject_uc: RejectBatchUseCase = Depends(get_reject_batch_use_case)):
    """Rechaza masivamente todos los casos pendientes de un lote."""
    try:
        rejected_count = await reject_uc.execute(batch_id=batch_id, user_id=HARDCODED_USER_ID, reason=payload.reason)
        return {"batch_id": str(batch_id), "rejected_count": rejected_count, "message": f"{rejected_count} expedientes rechazados"}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/{batch_id}/cases", response_model=PaginatedTriageResponse)
async def get_cases_by_batch(
    batch_id: UUID,
    skip: int = 0,
    limit: int = 100,
    use_case: GetCasesByBatchUseCase = Depends(get_cases_by_batch_use_case)
):
    """Devuelve la lista de expedientes de triaje que pertenecen a un lote (batch) específico."""
    return await use_case.execute(batch_id, skip=skip, limit=limit)

@router.post("/{batch_id}/verify-completion")
async def verify_batch_completion(batch_id: UUID, uc: VerifyBatchCompletionUseCase = Depends(get_verify_batch_completion_use_case)):
    """Verifica si todos los expedientes de un lote están aprobados y emite un evento si es así."""
    return await uc.execute(batch_id)

@router.get("/{batch_id}/summary")
async def get_batch_summary(batch_id: UUID, uc: GetBatchSummaryUseCase = Depends(get_batch_summary_use_case)):
    """Obtiene un resumen de la cantidad de expedientes aprobados y pendientes de un lote específico."""
    return await uc.execute(batch_id)

@router.get("/verdicts", summary="Obtiene la lista de veredictos de triaje")
async def get_triage_verdicts():
    """Devuelve los veredictos de triaje válidos (AUTO_APPROVED, REQUIRES_TRIAGE, etc)."""
    return [v.value for v in TriageVerdict]

@router.get("/statuses", summary="Obtiene la lista de estados del expediente de triaje")
async def get_triage_statuses():
    """Devuelve los estados de triaje válidos (PENDING_REVIEW, APPROVED, etc)."""
    return [s.value for s in TriageStatus]
