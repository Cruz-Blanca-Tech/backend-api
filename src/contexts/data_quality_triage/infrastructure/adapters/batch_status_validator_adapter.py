from uuid import UUID
from src.contexts.data_quality_triage.domain.shared.ports.batch_status_validator import BatchStatusValidatorPort
from src.contexts.document_intake_ocr.domain.repositories.batch_repository import BatchRepository
from src.contexts.document_intake_ocr.domain.entities.extraction_batch import BatchStatus

class BatchStatusValidatorAdapter(BatchStatusValidatorPort):
    def __init__(self, batch_repository: BatchRepository):
        self.batch_repository = batch_repository

    async def is_batch_ready_for_triage(self, batch_id: UUID) -> bool:
        batch = await self.batch_repository.get_by_id(batch_id)
        if not batch:
            return False
            
        # El lote está listo si NO está en proceso de extracción
        return batch.status != BatchStatus.PROCESSING

    async def is_batch_rejectable(self, batch_id: UUID) -> bool:
        batch = await self.batch_repository.get_by_id(batch_id)
        if not batch:
            return False
            
        # Solo se puede rechazar si el lote está pendiente de triaje (PENDING)
        return batch.status == BatchStatus.PENDING

    async def is_batch_completed(self, batch_id: UUID) -> bool:
        batch = await self.batch_repository.get_by_id(batch_id)
        if not batch:
            return False
            
        # El lote está completado si está en estado FINALIZED, FAILED o REJECTED
        return batch.status in (BatchStatus.FINALIZED, BatchStatus.FAILED, BatchStatus.REJECTED)
