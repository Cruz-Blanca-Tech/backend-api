from src.contexts.document_intake_ocr.domain.entities.extraction_batch import ExtractionBatch, BatchStatus
from src.contexts.document_intake_ocr.infrastructure.persistence.mappers.document_item_mapper import DocumentItemMapper
from src.contexts.document_intake_ocr.infrastructure.persistence.model.extraction_batch_model import ExtractionBatchModel

class BatchMapper:
    @staticmethod
    def to_model(entity: ExtractionBatch) -> ExtractionBatchModel:
        model = ExtractionBatchModel(
            id=entity.id,
            activity_id=entity.activity_id,
            created_by=entity.created_by,
            status=entity.status.value,
            created_at=entity.created_at
        )
        model.documents = [
            DocumentItemMapper.to_model(doc_entity, batch_id=entity.id) 
            for doc_entity in entity.documents
        ]   
        return model


    @staticmethod
    def to_domain(model: ExtractionBatchModel) -> ExtractionBatch:
        documents = [
            DocumentItemMapper.to_domain(doc_model) 
            for doc_model in model.documents
        ]   
        return ExtractionBatch(
            id=model.id,
            activity_id=model.activity_id,
            created_by=model.created_by,
            status=BatchStatus(model.status),
            documents=documents,
            created_at=model.created_at
        )

