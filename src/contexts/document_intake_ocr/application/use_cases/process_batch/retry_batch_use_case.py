from uuid import UUID
from fastapi import BackgroundTasks
from src.core.validators.exceptions import EntityNotFoundException, DomainValidationError
from src.contexts.document_intake_ocr.domain.repositories.batch_repository import BatchRepository
from src.contexts.document_intake_ocr.domain.entities.extraction_batch import BatchStatus
from src.contexts.document_intake_ocr.application.use_cases.process_batch.batch_processing_orchestrator import BatchProcessingOrchestrator

class RetryBatchUseCase:
    def __init__(
        self, 
        batch_repo: BatchRepository, 
        batch_orchestrator: BatchProcessingOrchestrator
    ):
        self.batch_repo = batch_repo
        self.batch_orchestrator = batch_orchestrator

    async def execute(
        self, 
        batch_id: UUID, 
        user_email: str, 
        background_tasks: BackgroundTasks
    ) -> dict:
        batch = await self.batch_repo.get_by_id(batch_id)
        if not batch:
            raise EntityNotFoundException("El lote no existe")

        if batch.status not in [BatchStatus.FAILED, BatchStatus.PENDING]:
            raise DomainValidationError("Solo se pueden reintentar lotes que hayan fallado o esten atascados en pendiente")

        # Cambiar el estado inmediatamente para reflejar que comenzo el reintento
        batch.status = BatchStatus.PROCESSING
        await self.batch_repo.save(batch)

        # Encolar la tarea asincrona reutilizando la logica existente
        background_tasks.add_task(self.batch_orchestrator.run_pipeline, batch.id, user_email)

        return {"message": "Reintento de OCR iniciado correctamente", "batch_id": str(batch.id)}
