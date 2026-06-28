import logging
from uuid import UUID, uuid4
from sqlalchemy.ext.asyncio import AsyncSession

from src.contexts.data_quality_triage.domain.shared.events.triage_events import BatchRejectedEvent
from src.contexts.data_quality_triage.infrastructure.persistence.repositories.sql_triage_repository import SqlTriageRepository
from src.contexts.data_quality_triage.infrastructure.persistence.model.triage_audit_log_model import TriageAuditLogModel
from src.core.events.event_dispatcher import EventDispatcher
from src.core.validators.exceptions import EntityNotFoundException

logger = logging.getLogger(__name__)

class RejectBatchUseCase:
    def __init__(self, triage_repo: SqlTriageRepository, session: AsyncSession):
        self.triage_repo = triage_repo
        self.session = session

    async def execute(self, batch_id: UUID, user_id: UUID, reason: str) -> int:
        cases = await self.triage_repo.get_all_by_batch_id(batch_id)
        if not cases: 
            raise EntityNotFoundException(f"No se encontraron casos de triaje para el lote {batch_id}")

        rejected_count = 0
        all_document_ids = []
        all_case_ids = []
        
        for case in cases:
            if case.is_finalized: 
                continue
                
            previous_status = case.status.value
            case.reject(user_id, reason)
            rejected_count += 1
            all_case_ids.append(case.id)
            all_document_ids.extend(case.document_ids.values())
            
            self._add_audit_log(case.id, "BATCH_REJECTED", user_id, previous_status, case.status.value, {"reason": reason, "batch_rejection": True})

        await self.triage_repo.bulk_save(cases)
        
        if all_document_ids:
            batch_event = BatchRejectedEvent(batch_id=batch_id, triage_case_ids=all_case_ids, document_ids=all_document_ids, rejected_by=user_id, reason=reason)
            await EventDispatcher.dispatch(batch_event)

        for case in cases:
            for event in case.pending_events: 
                await EventDispatcher.dispatch(event)
            case.clear_events()
            
        await self.session.commit()
        return rejected_count

    def _add_audit_log(self, case_id: UUID, action: str, performed_by: UUID, previous_status: str, new_status: str, details: dict = None) -> None:
        audit_log = TriageAuditLogModel(id=uuid4(), triage_case_id=case_id, action=action, performed_by=performed_by, previous_status=previous_status, new_status=new_status, details=details)
        self.session.add(audit_log)
