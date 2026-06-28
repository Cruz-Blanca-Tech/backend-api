from uuid import UUID
from src.contexts.data_quality_triage.domain.shared.repositories.triage_repository import TriageRepository
from src.contexts.data_quality_triage.domain.shared.value_objects.triage_status import TriageStatus
from src.contexts.data_quality_triage.domain.shared.value_objects.field_discrepancy import FieldDiscrepancy
from src.contexts.data_quality_triage.application.shared.factories.dossier_factory import DossierFactory
from src.contexts.data_quality_triage.domain.shared.value_objects.activity_type import ActivityType
from src.contexts.data_quality_triage.domain.shared.strategies.strategy_factory import DossierStrategyFactory

class RevalidateTriageCaseUseCase:
    def __init__(self, case_repo: TriageRepository):
        self.case_repo = case_repo

    async def execute(self, case_id: UUID, reviewer_id: UUID) -> None:
        """
        Re-ejecuta las reglas de dominio sobre los datos actuales del caso (corrected_data si existe,
        o documents_snapshot si aún no hay correcciones) y actualiza su estado.
        """
        case = await self.case_repo.get_by_id(case_id)
        if not case:
            raise ValueError(f"Triage Case {case_id} not found")

        inscription = DossierFactory.reconstitute(case.dossier_data, ActivityType(case.activity_type))

        is_valid, issues = inscription.validate_completeness()

        if is_valid:
            case.approve(reviewer_id)
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
