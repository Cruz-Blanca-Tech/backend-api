from uuid import UUID
from src.contexts.data_quality_triage.domain.shared.repositories.triage_repository import TriageRepository
from src.contexts.data_quality_triage.domain.shared.value_objects.triage_status import TriageStatus
from src.contexts.data_quality_triage.domain.shared.value_objects.field_discrepancy import FieldDiscrepancy
from src.contexts.data_quality_triage.application.educa.schemas.educa_inscription_schemas import (
    EducaInscriptionRequest, EducaInscriptionResponse, EducaInscriptionData
)
from src.contexts.data_quality_triage.application.shared.factories.dossier_factory import DossierFactory
from src.contexts.data_quality_triage.domain.shared.value_objects.activity_type import ActivityType

HARDCODED_USER_ID = UUID("00000000-0000-0000-0000-000000000001")

class UpdateDossierUseCase:
    def __init__(self, case_repo: TriageRepository):
        self.case_repo = case_repo

    async def execute(self, case_id: UUID, request: EducaInscriptionRequest) -> EducaInscriptionResponse:
        """
        Fase 2: El operador envía correcciones manuales.
        Se reconstruye el dominio desde el request, se valida completitud y se actualiza el caso.
        """
        case = await self.case_repo.get_by_id(case_id)
        if not case:
            raise ValueError(f"Triage Case {case_id} not found")

        # Persistir la corrección del operador en el caso
        case.dossier_data = request.model_dump(exclude_unset=True)

        # Reconstituir el dominio desde la corrección y validar
        inscription = DossierFactory.reconstitute(case.dossier_data, ActivityType.EDUCA_INSCRIPTION)
        is_valid, issues = inscription.validate_completeness()

        if is_valid:
            case.approve(HARDCODED_USER_ID)
            case.discrepancies = []
        else:
            case.status = TriageStatus.PENDING_REVIEW
            case.discrepancies = [
                FieldDiscrepancy(
                    field_name="completeness", expected_pattern="Completitud de datos",
                    actual_value="Falta información", rule_description=issue,
                    severity="ERROR", document_code="GLOBAL"
                ) for issue in issues
            ]

        await self.case_repo.save(case)

        domain_schema = EducaInscriptionData.model_validate(inscription, from_attributes=True)
        return EducaInscriptionResponse(
            case_id=str(case.id),
            status=case.status.value,
            is_valid=is_valid,
            issues=issues,
            domain_data=domain_schema
        )
