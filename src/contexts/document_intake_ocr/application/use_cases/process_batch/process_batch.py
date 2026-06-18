# src/contexts/document_intake_ocr/application/use_cases/batch/process_batch_use_case.py

from uuid import UUID
from fastapi import BackgroundTasks

from src.contexts.document_intake_ocr.application.mappers.process_batch_mapper import BatchExtractorMapper
from src.contexts.document_intake_ocr.application.use_cases.process_batch.batch_processing_orchestrator import BatchProcessingOrchestrator
from src.contexts.document_intake_ocr.domain.repositories.activity_repository import ActivityRepository
from src.contexts.document_intake_ocr.domain.repositories.batch_repository import BatchRepository
from src.contexts.document_intake_ocr.domain.factories.extraction_batch_factory import ExtractionBatchFactory
from src.contexts.document_intake_ocr.application.mappers.raw_file_mapper import RawFileMapper
from src.contexts.document_intake_ocr.application.schemas.batch_schema import ProcessBatchRequest, ProcessBatchResponse
from src.core.validators.exceptions import EntityNotFoundException

class ProcessBatchUseCase:
    """
    Orquestador síncrono: Delega la creación al dominio, persiste el estado
    inicial y dispara el procesamiento en segundo plano.
    """
    def __init__(
        self, 
        activity_repo: ActivityRepository, 
        batch_repo: BatchRepository,
        batch_orchestrator: BatchProcessingOrchestrator
    ):
        self.activity_repo = activity_repo
        self.batch_repo = batch_repo
        self.batch_orchestrator = batch_orchestrator

    async def execute(
        self, 
        request: ProcessBatchRequest, 
        user_id: UUID, 
        user_email: str, 
        background_tasks: BackgroundTasks
    ) -> ProcessBatchResponse:
        
        # 1. Recuperar contexto de BD
        activity = await self.activity_repo.get_by_id(request.activity_id)
        if not activity:
            raise EntityNotFoundException("Activity not found")

        # 2. Mapeo a Value Objects (Infraestructura -> Dominio)
        raw_files = [RawFileMapper.to_domain(f) for f in request.files]
        
        # 3. DELEGACIÓN AL DOMINIO: La Fábrica construye el Agregado complejo
        # Aquí encapsulamos todo el filtro, agrupación y creación de dossiers
        batch = ExtractionBatchFactory.create_from_raw_files(
            raw_files=raw_files, 
            activity=activity, 
            user_id=user_id
        )

        # 4. Persistencia transaccional inicial
        # Marcamos el lote como "En proceso" antes de disparar el worker
        batch.mark_as_processing()
        await self.batch_repo.save(batch)
        
        # 5. Disparo del pipeline de infraestructura asíncrono
        background_tasks.add_task(self.batch_orchestrator.run_pipeline, batch.id, user_email)

        # 6. MAPEADO Y RETORNO (Dominio -> DTO de Respuesta)
        return BatchExtractorMapper.to_response(
            batch=batch, 
            message="Validación inicial completada. El OCR se está ejecutando en segundo plano."
        )