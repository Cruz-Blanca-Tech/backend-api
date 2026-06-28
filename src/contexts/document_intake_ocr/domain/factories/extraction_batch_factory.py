# src/contexts/document_intake_ocr/domain/factories/extraction_batch_factory.py

from datetime import datetime, timezone
from uuid import UUID, uuid4
from typing import List

from src.contexts.document_intake_ocr.domain.entities.extraction_batch import ExtractionBatch
from src.contexts.document_intake_ocr.domain.entities.activity import Activity
from src.contexts.document_intake_ocr.domain.entities.document import DocumentItem
from src.contexts.document_intake_ocr.domain.services.document_filter_service import DocumentFilterService
from src.contexts.document_intake_ocr.domain.services.document_grouper_service import DocumentGrouperService
from src.contexts.document_intake_ocr.domain.factories.dossier_factory import DossierFactory
from src.contexts.document_intake_ocr.domain.value_objects.raw_file import RawFile

class ExtractionBatchFactory:
    """
    Fábrica experta en construir un Lote de Extracción (Agregado Raíz) 
    aplicando todas las reglas de filtrado y agrupación del dominio.
    """
    @staticmethod
    def create_from_raw_files(raw_files: List[RawFile], activity: Activity, user_id: UUID) -> ExtractionBatch:
        # 1. Clasificación inmediata (incluye validación del código contra el catálogo de la actividad)
        clean_files, rejected_files = DocumentFilterService.filter_batch(raw_files, activity)
        # 2. Agrupación
        proposals = DocumentGrouperService.group_valid_files(clean_files)

        # 3. Instanciación del Agregado
        batch = ExtractionBatch(id=uuid4(), activity_id=activity.id, created_by=user_id, created_at=datetime.now(timezone.utc))
        
        # 4. Ensamblaje de Expedientes
        for prop in proposals:
            dossier = DossierFactory.create_from_proposal(
                clean_proposal=prop,
                activity=activity, 
                batch_id=batch.id
            )
            batch.add_dossier(dossier)

        # 5. Adjuntar Rechazados
        for f in rejected_files:
            dni_ref = f.file.extracted_dni
            rejected_doc = DocumentItem.create_failed(
                source_id=f.file.source_id,
                file_name=f.file.file_name,
                dni_ref=dni_ref,
                reason=f.reason
            )
            batch.add_rejected_document(rejected_doc)

        return batch