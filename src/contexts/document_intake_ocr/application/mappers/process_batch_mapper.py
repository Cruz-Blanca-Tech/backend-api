# src/contexts/document_intake_ocr/presentation/mappers/batch_presentation_mapper.py

from src.contexts.document_intake_ocr.domain.entities.extraction_batch import ExtractionBatch
from src.contexts.document_intake_ocr.application.schemas.batch_schema import FailedDocumentDetail, ProcessBatchResponse

class BatchExtractorMapper:
    """
    Mapper de la capa de presentación. 
    Traduce las entidades de dominio puro a contratos (Schemas) de salida.
    """

    @staticmethod
    def to_response(batch: ExtractionBatch, message: str) -> ProcessBatchResponse:
        
        failed_files = [
            FailedDocumentDetail(
                file_name=doc.file_name,
                reason=doc.failure_reason or "Error de validación desconocido"
            )
            for doc in batch.rejected_documents
        ]
        
        return ProcessBatchResponse(
            batch_id=batch.id,
            batch_status=batch.status.value,
            total_dossiers=len(batch.dossiers),
            total_failed_files=len(batch.rejected_documents),
            failed_files=failed_files,
            message=message
        )