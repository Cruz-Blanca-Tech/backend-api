from uuid import UUID
from typing import Dict, Any
import logging
from fastapi import APIRouter, Depends, HTTPException

from src.contexts.data_quality_triage.application.shared.schemas.triage_schemas import (
    TriageCaseDetailResponse, DiscrepancySchema
)
from src.contexts.data_quality_triage.infrastructure.dependencies.triage_deps import (
    get_triage_repository, get_submit_correction_use_case
)
from src.contexts.data_quality_triage.infrastructure.persistence.repositories.sql_triage_repository import SqlTriageRepository
from src.contexts.data_quality_triage.application.shared.use_cases.submit_correction_use_case import SubmitCorrectionUseCase

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/dossier", tags=["Triage Dossiers"])

HARDCODED_USER_ID = UUID("00000000-0000-0000-0000-000000000001")

@router.get("/{case_id}", response_model=TriageCaseDetailResponse)
async def get_triage_case_detail(
    case_id: UUID,
    triage_repo: SqlTriageRepository = Depends(get_triage_repository)
):
    """
    Recupera el expediente de triage genérico con todo su snapshot, scores y discrepancias.
    """
    case = await triage_repo.get_by_id(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    discrepancies = [
        DiscrepancySchema(
            field_name=d.field_name, expected_pattern=d.expected_pattern,
            actual_value=d.actual_value, rule_description=d.rule_description,
            severity=d.severity, document_code=d.document_code,
        ) for d in case.discrepancies
    ]

    return TriageCaseDetailResponse(
        id=case.id, batch_id=case.batch_id, dni_reference=case.dni_reference,
        status=case.status.value, verdict=case.verdict.value,
        confidence_scores=case.confidence_scores, confidence_threshold=0.0, # Deprecated field but still in schema
        documents_snapshot=case.documents_snapshot, corrected_data=case.corrected_data,
        effective_data=case.effective_data, discrepancies=discrepancies,
        rejection_reason=case.rejection_reason, resolved_by=case.resolved_by,
        resolved_at=case.resolved_at, created_at=case.created_at, updated_at=case.updated_at,
    )

@router.patch("/{case_id}", response_model=TriageCaseDetailResponse)
async def submit_correction(
    case_id: UUID,
    payload: Dict[str, Dict[str, Any]],
    submit_correction_uc: SubmitCorrectionUseCase = Depends(get_submit_correction_use_case)
):
    """
    Guarda las correcciones manuales hechas sobre un expediente genérico.
    El caso ya conoce su activity_type.
    """
    case = await submit_correction_uc.execute(
        case_id=case_id, 
        user_id=HARDCODED_USER_ID,
        corrected_data=payload 
    )

    discrepancies = [
        DiscrepancySchema(
            field_name=d.field_name, expected_pattern=d.expected_pattern,
            actual_value=d.actual_value, rule_description=d.rule_description,
            severity=d.severity, document_code=d.document_code,
        ) for d in case.discrepancies
    ]

    return TriageCaseDetailResponse(
        id=case.id, batch_id=case.batch_id, dni_reference=case.dni_reference,
        status=case.status.value, verdict=case.verdict.value,
        confidence_scores=case.confidence_scores, confidence_threshold=0.0,
        documents_snapshot=case.documents_snapshot, corrected_data=case.corrected_data,
        effective_data=case.effective_data, discrepancies=discrepancies,
        rejection_reason=case.rejection_reason, resolved_by=case.resolved_by,
        resolved_at=case.resolved_at, created_at=case.created_at, updated_at=case.updated_at,
    )

@router.post("/manual-trigger", status_code=202)
async def manual_triage_trigger(batch_id: UUID, dni_reference: str, activity_type: str):
    """
    Endpoint de rescate/soporte técnico: 
    Dispara manualmente el motor de Triage simulando el OCR.
    """
    from src.core.events.event_dispatcher import EventDispatcher
    from src.contexts.shared.events.documents_extracted_event import DocumentsExtractedEvent
    
    event = DocumentsExtractedEvent(
        batch_id=batch_id,
        activity_type=activity_type,
        dni_reference=dni_reference
    )
    
    await EventDispatcher.dispatch(event)
    
    return {
        "status": "accepted",
        "message": f"Señal de triage enviada manualmente para el DNI {dni_reference} con actividad {activity_type}",
        "action_required": "Revisa la bandeja de entrada (/batch/{batch_id}) en unos segundos"
    }
