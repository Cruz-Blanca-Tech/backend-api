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

        # D6: un lote COMPLETED que tiene documentos fallidos tambien se puede reintentar.
        has_failed_docs = any(d.status.value == "FAILED" for d in batch.get_all_documents())
        retryable = batch.status in [BatchStatus.FAILED, BatchStatus.PENDING] or (
            batch.status == BatchStatus.COMPLETED and has_failed_docs
        )
        if not retryable:
            raise DomainValidationError(
                "Solo se pueden reintentar lotes que hayan fallado, esten atascados en pendiente "
                "o tengan documentos fallidos"
            )

        # Cambiar el estado inmediatamente para reflejar que comenzo el reintento
        batch.status = BatchStatus.PROCESSING
        await self.batch_repo.save(batch)

        # Encolar la tarea asincrona reutilizando la logica existente
        background_tasks.add_task(self.batch_orchestrator.run_pipeline, batch.id, user_email, True)

        return {"message": "Reintento de OCR iniciado correctamente", "batch_id": str(batch.id)}
