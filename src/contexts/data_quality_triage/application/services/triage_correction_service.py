import logging
from typing import Dict, Any
from uuid import UUID, uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from src.contexts.data_quality_triage.domain.entities.triage_case import TriageCase
from src.contexts.data_quality_triage.domain.strategies.strategy_factory import DossierStrategyFactory
from src.contexts.data_quality_triage.domain.value_objects.triage_status import TriageStatus
from src.contexts.data_quality_triage.domain.events.triage_events import BatchRejectedEvent
from src.contexts.data_quality_triage.infrastructure.persistence.repositories.sql_triage_repository import SqlTriageRepository
from src.contexts.data_quality_triage.infrastructure.persistence.model.triage_audit_log_model import TriageAuditLogModel
from src.core.events.event_dispatcher import EventDispatcher
from src.core.validators.exceptions import EntityNotFoundException

logger = logging.getLogger(__name__)

class TriageCorrectionService:
    def __init__(self, triage_repo: SqlTriageRepository, strategy_factory: DossierStrategyFactory, session: AsyncSession):
        self.triage_repo = triage_repo
        self.strategy_factory = strategy_factory
        self.session = session

    async def submit_correction(self, case_id: UUID, corrected_data: Dict[str, Dict[str, Any]], user_id: UUID) -> TriageCase:
        case = await self._get_case_or_fail(case_id)
        previous_status = case.status.value
        case.submit_correction(corrected_data, user_id)
        
        strategy = self.strategy_factory.get_strategy_for_documents(set(case.documents_snapshot.keys()))
        quality_result = strategy.validate(dossier_documents=case.effective_data, confidence_scores=case.confidence_scores, confidence_threshold=case.confidence_threshold)

        if quality_result.is_valid:
            case.approve(user_id)
            self._add_audit_log(case_id, "CORRECTED", user_id, previous_status, TriageStatus.CORRECTED.value, {"corrected_fields": corrected_data})
            self._add_audit_log(case_id, "APPROVED", user_id, TriageStatus.CORRECTED.value, case.status.value, {"verdict": case.verdict.value})
        else:
            case.update_discrepancies(quality_result.discrepancies)
            case.status = TriageStatus.PENDING_REVIEW
            self._add_audit_log(case_id, "CORRECTED", user_id, previous_status, case.status.value, {"corrected_fields": corrected_data, "remaining_errors": quality_result.error_count})

        await self.triage_repo.save(case)
        for event in case.pending_events:
            await EventDispatcher.dispatch(event)
        case.clear_events()
        await self.session.commit()
        return case

    async def approve_case(self, case_id: UUID, user_id: UUID) -> TriageCase:
        case = await self._get_case_or_fail(case_id)
        previous_status = case.status.value
        case.approve(user_id)
        self._add_audit_log(case_id, "APPROVED", user_id, previous_status, case.status.value, {"verdict": case.verdict.value})
        await self.triage_repo.save(case)
        for event in case.pending_events: await EventDispatcher.dispatch(event)
        case.clear_events()
        await self.session.commit()
        return case

    async def reject_case(self, case_id: UUID, user_id: UUID, reason: str) -> TriageCase:
        case = await self._get_case_or_fail(case_id)
        previous_status = case.status.value
        case.reject(user_id, reason)
        self._add_audit_log(case_id, "REJECTED", user_id, previous_status, case.status.value, {"reason": reason})
        await self.triage_repo.save(case)
        for event in case.pending_events: await EventDispatcher.dispatch(event)
        case.clear_events()
        await self.session.commit()
        return case

    async def reject_batch(self, batch_id: UUID, user_id: UUID, reason: str) -> int:
        cases = await self.triage_repo.get_all_by_batch_id(batch_id)
        if not cases: raise EntityNotFoundException(f"No se encontraron casos de triaje para el lote {batch_id}")

        rejected_count = 0
        all_document_ids = []
        all_case_ids = []
        for case in cases:
            if case.is_finalized: continue
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
            for event in case.pending_events: await EventDispatcher.dispatch(event)
            case.clear_events()
        await self.session.commit()
        return rejected_count

    async def _get_case_or_fail(self, case_id: UUID) -> TriageCase:
        case = await self.triage_repo.get_by_id(case_id)
        if not case: raise EntityNotFoundException(f"No se encontr? el caso de triaje con ID: {case_id}")
        return case

    def _add_audit_log(self, case_id: UUID, action: str, performed_by: UUID, previous_status: str, new_status: str, details: dict = None) -> None:
        audit_log = TriageAuditLogModel(id=uuid4(), triage_case_id=case_id, action=action, performed_by=performed_by, previous_status=previous_status, new_status=new_status, details=details)
        self.session.add(audit_log)
