# src/contexts/document_intake_ocr/application/use_cases/batch/process_batch_use_case.py

from uuid import UUID, uuid4
from fastapi import BackgroundTasks
from typing import List

from src.contexts.document_intake_ocr.domain.entities.extraction_batch import ExtractionBatch
from src.contexts.document_intake_ocr.domain.entities.document import DocumentItem
from src.contexts.document_intake_ocr.domain.repositories.activity_repository import ActivityRepository
from src.contexts.document_intake_ocr.domain.repositories.batch_repository import BatchRepository
from src.contexts.document_intake_ocr.domain.services.document_filter_service import DocumentFilterService
from src.contexts.document_intake_ocr.domain.services.document_grouper_service import DocumentGrouperService
from src.contexts.document_intake_ocr.domain.factories.dossier_factory import DossierFactory
from src.contexts.document_intake_ocr.application.mappers.raw_file_mapper import RawFileMapper
from src.contexts.document_intake_ocr.application.schemas.batch_schema import ProcessBatchRequest

class ProcessBatchUseCase:
    """
    Orquestador definitivo: Coordina el flujo de ingesta documental, 
    asegurando la integridad del dominio y la persistencia de resultados.
    """
    def __init__(self, activity_repo: ActivityRepository, batch_repo: BatchRepository):
        self.activity_repo = activity_repo
        self.batch_repo = batch_repo

    async def execute(self, request: ProcessBatchRequest, user_id: UUID, background_tasks: BackgroundTasks):
        
        # 1. Recuperar contexto (Actividad como Experto en Información)
        activity = await self.activity_repo.get_by_id(request.activity_id)
        if not activity:
            raise ValueError("Activity not found")

        # 2. Transformación a Value Objects
        raw_files = [RawFileMapper.to_domain(f) for f in request.files]
        
        # 3. FILTRO GLOBAL: Clasificación inmediata (Válidos vs Rechazados)
        clean_files, rejected_files = DocumentFilterService.filter_batch(raw_files)

        # 4. AGRUPACIÓN: Solo procesamos archivos garantizados
        proposals = DocumentGrouperService.group_valid_files(clean_files)

        # 5. Creación del Agregado Raíz (Batch)
        batch = ExtractionBatch(id=uuid4(), activity_id=activity.id, created_by=user_id)
        
        # 6. Ensamblaje de Expedientes (Dossiers)
        for prop in proposals:
            dossier = DossierFactory.create_from_proposal(
                clean_proposal=prop,
                activity=activity, 
                batch_id=batch.id
            )
            batch.add_dossier(dossier)

        # 7. Persistencia de Rechazados
        for f in rejected_files:
            dni_ref = str(f.file.extracted_dni.value) if f.file.extracted_dni else "UNKNOWN"            
            rejected_doc = DocumentItem.create_failed(
                source_uri=f.file.source_uri,
                file_name=f.file.file_name,
                dni_ref=dni_ref,
                reason=f.reason
            )
            batch.add_rejected_document(rejected_doc)

        await self.batch_repo.save(batch)
        
        # 9. Disparo de pipeline asíncrono
        background_tasks.add_task(self._run_async_pipeline, batch.id)

        return batch

    async def _run_async_pipeline(self, batch_id: UUID) -> None:
        """Entrada del Worker para procesamiento OCR asíncrono."""
        pass