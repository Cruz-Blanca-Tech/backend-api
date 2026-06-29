import logging
from uuid import UUID
from src.contexts.data_quality_triage.domain.shared.repositories.triage_repository import TriageRepository
from src.contexts.data_quality_triage.domain.shared.value_objects.triage_status import TriageVerdict, BatchVerificationStatus
from src.contexts.shared.events.batch_triage_completed_event import BatchTriageCompletedEvent
from src.core.events.event_dispatcher import EventDispatcher

logger = logging.getLogger(__name__)

class VerifyBatchCompletionUseCase:
    def __init__(self, triage_repository: TriageRepository):
        self.triage_repository = triage_repository

    async def execute(self, batch_id: UUID) -> dict:
        cases = await self.triage_repository.get_all_by_batch_id(batch_id)
        
        verdict_summary = {v.name: 0 for v in TriageVerdict}

        if not cases:
            return {
                "status": BatchVerificationStatus.NOT_FOUND, 
                "message": f"No triage cases found for batch {batch_id}",
                "verdict_summary": verdict_summary
            }
        
        all_processed = True
        pending_cases = 0

        
        for case in cases:
            verdict_name = case.verdict.name if hasattr(case.verdict, 'name') else case.verdict
            verdict_summary[verdict_name] = verdict_summary.get(verdict_name, 0) + 1
            
            # The only pending status that blocks completion is REQUIRES_TRIAGE
            if case.verdict == TriageVerdict.REQUIRES_TRIAGE:
                all_processed = False
                pending_cases += 1
                
        if all_processed:
            logger.info(f"All {len(cases)} cases for batch {batch_id} have been processed. Emitting completion event.")
            await EventDispatcher.dispatch(BatchTriageCompletedEvent(batch_id=batch_id))
            return {
                "status": BatchVerificationStatus.COMPLETED, 
                "message": f"Batch {batch_id} verified and marked as completed.",
                "verdict_summary": verdict_summary
            }
        else:
            return {
                "status": BatchVerificationStatus.PENDING, 
                "message": f"Batch {batch_id} has {pending_cases} pending cases.",
                "verdict_summary": verdict_summary
            }
