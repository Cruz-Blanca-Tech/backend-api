import logging
from uuid import UUID
from fastapi import APIRouter, Depends, Query

from src.contexts.data_quality_triage.application.schemas.triage_schemas import (
    BatchProcessingResult, TriageCaseDetailResponse, PaginatedTriageResponse, BatchTriageSummary, TriageCorrectionRequest, TriageRejectRequest, AuditLogEntry,
)
from src.contexts.data_quality_triage.infrastructure.dependencies.triage_deps import (
    get_dossier_processor, get_triage_correction_service, get_triage_query_service,
)
from src.contexts.data_quality_triage.application.services.dossier_processor import DossierProcessor
from src.contexts.data_quality_triage.application.services.triage_correction_service import TriageCorrectionService
from src.contexts.data_quality_triage.application.services.triage_query_service import TriageQueryService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Data Quality & Triage"])
HARDCODED_USER_ID = UUID("00000000-0000-0000-0000-000000000001")

@router.get("/health")
async def health_check():
    return {"status": "ok", "context": "Data Quality & Triage"}

@router.post("/process/{batch_id}", response_model=BatchProcessingResult)
async def process_batch(batch_id: UUID, processor: DossierProcessor = Depends(get_dossier_processor)):
    return await processor.process_batch(batch_id)

@router.get("/inbox", response_model=PaginatedTriageResponse)
async def get_triage_inbox(skip: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=100), query_service: TriageQueryService = Depends(get_triage_query_service)):
    return await query_service.get_triage_inbox(skip=skip, limit=limit)

@router.get("/{case_id}", response_model=TriageCaseDetailResponse)
async def get_case_detail(case_id: UUID, query_service: TriageQueryService = Depends(get_triage_query_service)):
    return await query_service.get_case_detail(case_id)

@router.get("/{case_id}/audit", response_model=list[AuditLogEntry])
async def get_audit_trail(case_id: UUID, query_service: TriageQueryService = Depends(get_triage_query_service)):
    return await query_service.get_audit_trail(case_id)

@router.patch("/fix/{case_id}", response_model=TriageCaseDetailResponse)
async def submit_correction(case_id: UUID, payload: TriageCorrectionRequest, correction_service: TriageCorrectionService = Depends(get_triage_correction_service), query_service: TriageQueryService = Depends(get_triage_query_service)):
    await correction_service.submit_correction(case_id=case_id, corrected_data=payload.corrected_fields, user_id=HARDCODED_USER_ID)
    return await query_service.get_case_detail(case_id)

@router.post("/{case_id}/approve", response_model=TriageCaseDetailResponse)
async def approve_case(case_id: UUID, correction_service: TriageCorrectionService = Depends(get_triage_correction_service), query_service: TriageQueryService = Depends(get_triage_query_service)):
    await correction_service.approve_case(case_id=case_id, user_id=HARDCODED_USER_ID)
    return await query_service.get_case_detail(case_id)

@router.post("/{case_id}/reject", response_model=TriageCaseDetailResponse)
async def reject_case(case_id: UUID, payload: TriageRejectRequest, correction_service: TriageCorrectionService = Depends(get_triage_correction_service), query_service: TriageQueryService = Depends(get_triage_query_service)):
    await correction_service.reject_case(case_id=case_id, user_id=HARDCODED_USER_ID, reason=payload.reason)
    return await query_service.get_case_detail(case_id)

@router.post("/batch/{batch_id}/reject")
async def reject_batch(batch_id: UUID, payload: TriageRejectRequest, correction_service: TriageCorrectionService = Depends(get_triage_correction_service)):
    rejected_count = await correction_service.reject_batch(batch_id=batch_id, user_id=HARDCODED_USER_ID, reason=payload.reason)
    return {"batch_id": str(batch_id), "rejected_count": rejected_count, "message": f"{rejected_count} expedientes rechazados"}

@router.get("/batch/{batch_id}/summary", response_model=BatchTriageSummary)
async def get_batch_summary(batch_id: UUID, query_service: TriageQueryService = Depends(get_triage_query_service)):
    return await query_service.get_batch_summary(batch_id)
