import logging
from uuid import UUID, uuid4
from sqlalchemy.ext.asyncio import AsyncSession

from src.contexts.data_quality_triage.domain.shared.entities.triage_case import TriageCase
from src.contexts.data_quality_triage.infrastructure.persistence.repositories.sql_triage_repository import SqlTriageRepository
from src.contexts.data_quality_triage.infrastructure.persistence.model.triage_audit_log_model import TriageAuditLogModel
from src.core.events.event_dispatcher import EventDispatcher
from src.core.validators.exceptions import EntityNotFoundException

logger = logging.getLogger(__name__)

class RejectDossierUseCase:
    def __init__(self, triage_repo: SqlTriageRepository, session: AsyncSession):
        self.triage_repo = triage_repo
        self.session = session

    async def execute(self, case_id: UUID, user_id: UUID, reason: str) -> TriageCase:
        case = await self.triage_repo.get_by_id(case_id)
        if not case:
            raise EntityNotFoundException(f"No se encontró el caso de triaje con ID: {case_id}")

        previous_status = case.status.value
        case.reject(user_id, reason)
        
        self._add_audit_log(case_id, "REJECTED", user_id, previous_status, case.status.value, {"reason": reason})
        
        await self.triage_repo.save(case)
        for event in case.pending_events: 
            await EventDispatcher.dispatch(event)
        case.clear_events()
        
        await self.session.commit()
        return case

    def _add_audit_log(self, case_id: UUID, action: str, performed_by: UUID, previous_status: str, new_status: str, details: dict = None) -> None:
        audit_log = TriageAuditLogModel(id=uuid4(), triage_case_id=case_id, action=action, performed_by=performed_by, previous_status=previous_status, new_status=new_status, details=details)
        self.session.add(audit_log)
