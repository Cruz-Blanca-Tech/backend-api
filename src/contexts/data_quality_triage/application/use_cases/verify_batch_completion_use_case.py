import logging
from uuid import UUID
from src.contexts.data_quality_triage.domain.shared.ports.batch_status_validator import BatchStatusValidatorPort
from src.contexts.data_quality_triage.domain.shared.repositories.triage_repository import TriageRepository
from src.contexts.data_quality_triage.domain.shared.value_objects.triage_status import TriageVerdict, BatchVerificationStatus, TriageStatus
from src.contexts.shared.events.batch_triage_completed_event import BatchTriageCompletedEvent
from src.contexts.shared.events.dossier_approved_event import DossierApprovedEvent
from src.core.events.event_dispatcher import EventDispatcher

logger = logging.getLogger(__name__)

class VerifyBatchCompletionUseCase:
    def __init__(self, triage_repository: TriageRepository, batch_status_validator: BatchStatusValidatorPort):
        self.triage_repository = triage_repository
        self.batch_status_validator = batch_status_validator

    async def execute(self, batch_id: UUID) -> dict:
        verdict_summary = {v.name: 0 for v in TriageVerdict}

        # Check if the batch has finished processing in the OCR engine
        is_ready = await self.batch_status_validator.is_batch_ready_for_triage(batch_id)
        if not is_ready:
            return {
                "status": BatchVerificationStatus.PENDING,
                "message": "No se puede verificar la finalización porque el motor OCR aún está procesando el lote.",
                "verdict_summary": verdict_summary
            }

        cases = await self.triage_repository.get_all_by_batch_id(batch_id)
        
        if not cases:
            return {
                "status": BatchVerificationStatus.NOT_FOUND, 
                "message": f"No triage cases found for batch {batch_id}",
                "verdict_summary": verdict_summary
            }
        
        all_processed = True
        pending_cases = 0
        has_rejections = False

        for case in cases:
            verdict_name = case.verdict.name if hasattr(case.verdict, 'name') else case.verdict
            verdict_summary[verdict_name] = verdict_summary.get(verdict_name, 0) + 1
            
            # The only pending status that blocks completion is REQUIRES_TRIAGE
            if case.verdict == TriageVerdict.REQUIRES_TRIAGE:
                all_processed = False
                pending_cases += 1
                
        if all_processed:
            logger.info(f"All {len(cases)} cases for batch {batch_id} have been processed. Emitting approved events per case and batch completion event.")
            for case in cases:
                if case.status == TriageStatus.APPROVED:
                    await EventDispatcher.dispatch(
                        DossierApprovedEvent(
                            triage_case_id=case.id,
                            batch_id=case.batch_id,
                            activity_type=case.activity_type,
                            dni_reference=case.dni_reference,
                            dossier_data=case.dossier_data,
                            approved_by=case.resolved_by or UUID("00000000-0000-0000-0000-000000000001")
                        )
                    )
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
