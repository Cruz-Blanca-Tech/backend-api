from uuid import UUID
import logging
from fastapi import APIRouter, Depends, HTTPException

from src.contexts.data_quality_triage.application.shared.schemas.triage_schemas import (
    TriageCaseDetailResponse, DiscrepancySchema, TriageRejectRequest
)
from src.contexts.data_quality_triage.application.educa.schemas.educa_inscription_schemas import EducaInscriptionData, EducaTriageCaseDetailResponse, EducaTriageCasePreviewResponse
from src.contexts.data_quality_triage.infrastructure.dependencies.triage_deps import (
    get_submit_correction_use_case, get_triage_repository, get_reject_dossier_use_case
)
from src.contexts.data_quality_triage.infrastructure.persistence.repositories.sql_triage_repository import SqlTriageRepository
from src.contexts.data_quality_triage.application.shared.use_cases.submit_correction_use_case import SubmitCorrectionUseCase
from src.contexts.data_quality_triage.application.shared.use_cases.reject_dossier_use_case import RejectDossierUseCase
from src.contexts.data_quality_triage.application.shared.factories.dossier_factory import DossierFactory
from src.contexts.data_quality_triage.domain.shared.value_objects.activity_type import ActivityType
from dataclasses import asdict

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/educa", tags=["Educa Triage"])

HARDCODED_USER_ID = UUID("00000000-0000-0000-0000-000000000001")

@router.get("/{case_id}", response_model=EducaTriageCasePreviewResponse)
async def get_educa_triage_case(
    case_id: UUID,
    triage_repo: SqlTriageRepository = Depends(get_triage_repository)
):
    """
    Recupera el expediente de triage específico de Educa.
    Devuelve la data fuertemente tipada con EducaInscriptionData.
    """
    case = await triage_repo.get_by_id(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Expediente no encontrado")
        
    if case.activity_type != "EDUCA_INSCRIPTION":
        raise HTTPException(
            status_code=400, 
            detail=f"Este endpoint es exclusivo para EDUCA_INSCRIPTION. El expediente pertenece a {case.activity_type}."
        )

    discrepancies = [
        DiscrepancySchema.from_domain(d) for d in case.discrepancies
    ]

    # Reconstruimos la entidad de dominio para asegurar integridad
    domain_entity = DossierFactory.reconstitute(case.dossier_data, ActivityType(case.activity_type))

    return EducaTriageCasePreviewResponse(
        status=case.status.value,
        dossier_data=asdict(domain_entity),
        discrepancies=discrepancies,
    )

@router.patch("/{case_id}", response_model=EducaTriageCaseDetailResponse)
async def submit_correction(
    case_id: UUID,
    payload: EducaInscriptionData,
    submit_correction_uc: SubmitCorrectionUseCase = Depends(get_submit_correction_use_case),
    triage_repo: SqlTriageRepository = Depends(get_triage_repository)
):
    """
    Guarda las correcciones manuales hechas sobre un expediente de Educa.
    Tipado fuertemente con EducaInscriptionData.
    """
    case_record = await triage_repo.get_by_id(case_id)
    if not case_record:
        raise HTTPException(status_code=404, detail="Expediente no encontrado")
        
    if case_record.activity_type != "EDUCA_INSCRIPTION":
        raise HTTPException(
            status_code=400, 
            detail=f"Este endpoint es exclusivo para EDUCA_INSCRIPTION. El expediente pertenece a {case_record.activity_type}."
        )

    case = await submit_correction_uc.execute(
        case_id=case_id, 
        user_id=HARDCODED_USER_ID,
        corrected_data=payload.model_dump()
    )

    discrepancies = [
        DiscrepancySchema.from_domain(d) for d in case.discrepancies
    ]

    return EducaTriageCaseDetailResponse(
        id=str(case.id), batch_id=str(case.batch_id), dni_reference=case.dni_reference,
        status=case.status.value, verdict=case.verdict.value,
        confidence_scores=case.confidence_scores,
        dossier_data=case.dossier_data,
        discrepancies=discrepancies,
    )

@router.post("/{case_id}/reject")
async def reject_triage_case(
    case_id: UUID,
    payload: TriageRejectRequest,
    reject_uc: RejectDossierUseCase = Depends(get_reject_dossier_use_case),
    triage_repo: SqlTriageRepository = Depends(get_triage_repository)
):
    """
    Rechaza un expediente específico de Educa, indicando un motivo.
    """
    case_record = await triage_repo.get_by_id(case_id)
    if not case_record:
        raise HTTPException(status_code=404, detail="Expediente no encontrado")
        
    if case_record.activity_type != "EDUCA_INSCRIPTION":
        raise HTTPException(
            status_code=400, 
            detail=f"Este endpoint es exclusivo para EDUCA_INSCRIPTION. El expediente pertenece a {case_record.activity_type}."
        )

    await reject_uc.execute(case_id=case_id, user_id=HARDCODED_USER_ID, reason=payload.reason)
    
    return {"case_id": str(case_id), "message": "Expediente rechazado correctamente"}

@router.post("/manual-trigger", status_code=202)
async def manual_triage_trigger(batch_id: UUID, dni_reference: str):
    """
    Endpoint de rescate/soporte técnico para Educa: 
    Dispara manualmente el motor de Triage simulando el OCR.
    """
    from src.core.events.event_dispatcher import EventDispatcher
    from src.contexts.shared.events.documents_extracted_event import DocumentsExtractedEvent
    
    activity_type = "EDUCA_INSCRIPTION"
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
