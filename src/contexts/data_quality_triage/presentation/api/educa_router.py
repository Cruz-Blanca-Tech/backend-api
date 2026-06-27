import logging
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException

from src.contexts.data_quality_triage.application.educa.schemas.educa_schemas import EducaInscriptionRequest, EducaInscriptionResponse
from src.contexts.data_quality_triage.application.shared.schemas.triage_schemas import TriageCaseDetailResponse
from src.contexts.data_quality_triage.infrastructure.dependencies.triage_deps import (
    get_triage_correction_service, get_triage_query_service,
)
from src.contexts.data_quality_triage.application.shared.services.triage_correction_service import TriageCorrectionService
from src.contexts.data_quality_triage.application.shared.services.triage_query_service import TriageQueryService
from src.contexts.data_quality_triage.application.shared.factories.dossier_factory import DossierFactory

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/educa", tags=["Educa Triage"])

HARDCODED_USER_ID = UUID("00000000-0000-0000-0000-000000000001")

@router.get("/{case_id}", response_model=EducaInscriptionResponse)
async def get_educa_case_detail(
    case_id: UUID,
    query_service: TriageQueryService = Depends(get_triage_query_service)
):
    """
    Recupera el expediente de triage en su estado actual (crudo + correcciones) 
    y lo devuelve empaquetado como el modelo canónico EducaInscription, 
    listo para que el Frontend lo monte en su formulario interactivo.
    """
    case = await query_service.triage_repo.get_by_id(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
        
    inscription = DossierFactory.from_data(case.effective_data)
    issues = [d.rule_description for d in case.discrepancies]
    
    return EducaInscriptionResponse(
        case_id=str(case.id),
        status=case.status.value,
        is_valid=len(issues) == 0,
        issues=issues,
        canonical_data=inscription.to_dict()
    )

@router.patch("/{case_id}", response_model=EducaInscriptionResponse)
async def submit_correction(
    case_id: UUID, 
    payload: EducaInscriptionRequest, 
    query_service: TriageQueryService = Depends(get_triage_query_service)
):
    """
    Guarda las correcciones manuales hechas sobre un expediente usando el contrato fuertemente tipado de Educa.
    Al recibir el modelo canónico, validamos su completitud y aprobamos el caso de triaje si es válido.
    """
    case = await query_service.triage_repo.get_by_id(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # 1. Guardar los datos canónicos como la corrección final
    canonical_dict = payload.model_dump(exclude_unset=True)
    case.corrected_data = canonical_dict
    
    # 2. Reconstruir el objeto de dominio para validarlo
    from src.contexts.data_quality_triage.domain.educa.value_objects.educa_inscription import EducaInscription
    from src.contexts.data_quality_triage.domain.educa.value_objects.beneficiary_data import BeneficiaryData
    from src.contexts.data_quality_triage.domain.educa.value_objects.family_data import FamilyData
    from src.contexts.data_quality_triage.domain.educa.value_objects.education_data import EducationData
    from src.contexts.data_quality_triage.domain.educa.value_objects.medical_data import MedicalData
    from src.contexts.data_quality_triage.domain.educa.value_objects.related_adult import RelatedAdult
    
    def clean_dict(d):
        return {k: v for k, v in d.items() if k != "validation_issues"} if d else {}
        
    ben_dict = clean_dict(canonical_dict.get("beneficiary", {}))
    edu_dict = clean_dict(canonical_dict.get("education", {}))
    med_dict = clean_dict(canonical_dict.get("medical", {}))
    
    fam_dict = clean_dict(canonical_dict.get("related_adults", {}))
    adults_list = []
    for ad_data in fam_dict.get("adults", []):
        adults_list.append(RelatedAdult(**ad_data))
        
    family_obj = FamilyData(
        adults=adults_list,
        guardian_dni=fam_dict.get("guardian_dni")
    )
        
    inscription = EducaInscription(
        beneficiary=BeneficiaryData(**ben_dict),
        related_adults=family_obj,
        education=EducationData(**edu_dict),
        medical=MedicalData(**med_dict)
    )

    # 3. Validar con la regla de negocio final de Educa
    is_valid, issues = inscription.validate_completeness()
    
    # 4. Actualizar estado del caso
    if is_valid:
        case.approve(HARDCODED_USER_ID)
        case.discrepancies = []  # Limpiamos errores anteriores porque ya es válido
    else:
        from src.contexts.data_quality_triage.domain.shared.value_objects.field_discrepancy import FieldDiscrepancy
        from src.contexts.data_quality_triage.domain.shared.value_objects.triage_status import TriageStatus
        
        # Regresamos el caso a revisión si fue aprobado previamente
        case.status = TriageStatus.PENDING_REVIEW
        
        # Convertimos los issues de negocio a discrepancias para que las vea el usuario
        case.discrepancies = [
            FieldDiscrepancy(
                field_name="completeness", expected_pattern="Completitud de datos", actual_value="Falta información",
                rule_description=issue, severity="ERROR", document_code="GLOBAL"
            ) for issue in issues
        ]
        
    await query_service.triage_repo.save(case)
    await query_service.session.commit()
    
    return EducaInscriptionResponse(
        case_id=str(case.id),
        status=case.status.value,
        is_valid=is_valid,
        issues=issues,
        canonical_data=inscription.to_dict()
    )
