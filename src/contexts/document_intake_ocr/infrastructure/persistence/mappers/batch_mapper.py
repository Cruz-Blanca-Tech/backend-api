import logging

from src.contexts.document_intake_ocr.domain.entities.document import DocumentStatus
from src.contexts.document_intake_ocr.domain.entities.dossier import Dossier
from src.contexts.document_intake_ocr.domain.entities.extraction_batch import ExtractionBatch, BatchStatus
from src.contexts.document_intake_ocr.infrastructure.persistence.mappers.document_item_mapper import DocumentItemMapper
from src.contexts.document_intake_ocr.infrastructure.persistence.model.extraction_batch_model import ExtractionBatchModel

logger = logging.getLogger(__name__)


class BatchMapper:
    @staticmethod
    def to_model(entity: ExtractionBatch) -> ExtractionBatchModel:
        model = ExtractionBatchModel(
            id=entity.id,
            activity_id=entity.activity_id,
            created_by=entity.created_by,
            status=entity.status.value,
            created_at=entity.created_at,
            description=entity.description
        )
        
        # We must gather ALL documents (valid from dossiers + rejected) to save them
        all_domain_docs = entity.get_all_documents() 
        
        model.documents = [
            DocumentItemMapper.to_model(doc_entity, batch_id=entity.id) 
            for doc_entity in all_domain_docs
        ]   
        
        return model

    @staticmethod
    def to_domain(model: ExtractionBatchModel) -> ExtractionBatch:
        # 1. Crear el Batch de dominio básico
        batch = ExtractionBatch(
            id=model.id,
            activity_id=model.activity_id,
            created_by=model.created_by,
            status=BatchStatus(model.status),
            created_at=model.created_at,
            description=model.description
        )
        
        # 2. CLASIFICAR documentos: los FALLIDOS son rechazados del lote,
        #    el resto se AGRUPA por DNI para reconstruir los Dossiers.
        #    (Sin esta separación, los documentos FAILED quedaban enterrados
        #     dentro de un dossier y batch.rejected_documents salía vacío, por lo
        #     que el GET de estado devolvía failed_files = []).
        dossiers_dict = {}

        for doc_model in model.documents:
            domain_doc = DocumentItemMapper.to_domain(doc_model)

            if domain_doc.status == DocumentStatus.FAILED:
                batch.add_rejected_document(domain_doc)
                continue

            # Protegemos por si algún documento no tiene DNI
            dni = doc_model.dni_reference or "SIN_DNI"

            if dni not in dossiers_dict:
                dossiers_dict[dni] = Dossier(
                    dni=dni,
                    activity_id=model.activity_id,
                    batch_id=model.id
                )

            dossiers_dict[dni].add_document(domain_doc)

        # 3. Registrar los dossiers en el Batch de dominio
        for dossier in dossiers_dict.values():
            batch.add_dossier(dossier)

        logger.debug(
            "BatchMapper.to_domain: %d expedientes (dossiers), %d documentos rechazados.",
            len(dossiers_dict), len(batch.rejected_documents)
        )

        return batch
