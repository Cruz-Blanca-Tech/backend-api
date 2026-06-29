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
