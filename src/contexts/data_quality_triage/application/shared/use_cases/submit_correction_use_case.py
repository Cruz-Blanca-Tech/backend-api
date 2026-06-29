import logging
from typing import Dict, Any
from uuid import UUID, uuid4
from sqlalchemy.ext.asyncio import AsyncSession

from src.contexts.data_quality_triage.domain.shared.entities.triage_case import TriageCase
from src.contexts.data_quality_triage.domain.shared.value_objects.triage_status import TriageStatus
from src.contexts.data_quality_triage.infrastructure.persistence.repositories.sql_triage_repository import SqlTriageRepository
from src.contexts.data_quality_triage.infrastructure.persistence.model.triage_audit_log_model import TriageAuditLogModel
from src.core.events.event_dispatcher import EventDispatcher
from src.core.validators.exceptions import EntityNotFoundException
from src.contexts.data_quality_triage.application.shared.factories.dossier_factory import DossierFactory
from src.contexts.data_quality_triage.domain.shared.value_objects.activity_type import ActivityType
from src.contexts.data_quality_triage.domain.shared.value_objects.field_discrepancy import FieldDiscrepancy

logger = logging.getLogger(__name__)

class SubmitCorrectionUseCase:
    def __init__(self, triage_repo: SqlTriageRepository, session: AsyncSession):
        self.triage_repo = triage_repo
        self.session = session

    async def execute(self, case_id: UUID, user_id: UUID, corrected_data: Dict[str, Any]) -> TriageCase:
        case = await self.triage_repo.get_by_id(case_id)
        if not case:
            raise EntityNotFoundException(f"No se encontró el caso de triaje con ID: {case_id}")
            
        if case.is_finalized:
            raise ValueError("No se puede editar un caso de triaje que ya ha sido finalizado (aprobado o rechazado).")

        previous_status = case.status.value
        case.submit_correction(corrected_data, user_id)
        
        try:
            activity_type = ActivityType(case.activity_type)
            domain_entity = DossierFactory.reconstitute(case.dossier_data, activity_type)
            is_complete, domain_issues = domain_entity.validate_completeness()
        except Exception as e:
            logger.error(f"Error reconstituting domain entity for correction validation: {str(e)}")
            is_complete = False
            domain_issues = [
                FieldDiscrepancy(
                    field_name="payload", expected_pattern="Formato válido", actual_value="Error",
                    rule_description=f"Error al parsear el payload: {str(e)}", severity="ERROR", document_code="GLOBAL"
                )
            ]

        if is_complete:
            case.approve(user_id)
            case.discrepancies = []
            self._add_audit_log(case_id, "CORRECTED", user_id, previous_status, TriageStatus.CORRECTED.value, {"corrected_fields": corrected_data})
            self._add_audit_log(case_id, "AUTO_APPROVED", user_id, TriageStatus.CORRECTED.value, case.status.value, {"verdict": case.verdict.value, "reason": "Validación manual exitosa"})
        else:
            case.update_discrepancies(domain_issues)
            case.status = TriageStatus.PENDING_REVIEW
            self._add_audit_log(case_id, "CORRECTED", user_id, previous_status, case.status.value, {"corrected_fields": corrected_data, "remaining_errors": len(domain_issues)})

        await self.triage_repo.save(case)
        for event in case.pending_events:
            await EventDispatcher.dispatch(event)
        case.clear_events()
        await self.session.commit()
        
        return case

    def _add_audit_log(self, case_id: UUID, action: str, performed_by: UUID, previous_status: str, new_status: str, details: dict = None) -> None:
        audit_log = TriageAuditLogModel(id=uuid4(), triage_case_id=case_id, action=action, performed_by=performed_by, previous_status=previous_status, new_status=new_status, details=details)
        self.session.add(audit_log)
