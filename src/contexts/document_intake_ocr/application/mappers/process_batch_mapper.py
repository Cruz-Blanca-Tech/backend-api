# src/contexts/document_intake_ocr/presentation/mappers/batch_presentation_mapper.py

from typing import List
from src.contexts.document_intake_ocr.domain.entities.extraction_batch import ExtractionBatch
from src.contexts.document_intake_ocr.application.schemas.batch_schema import ProcessBatchResponse

class BatchPresentationMapper:
    """
    Mapper de la capa de presentación. 
    Traduce las entidades de dominio puro a contratos (Schemas) de salida.
    """

    @staticmethod
    def to_response(  # <--- ¡Mucho más limpio y estándar!
        batch: ExtractionBatch, 
        accepted_dnis: List[str], 
        rejected_dnis: List[str], 
        invalid_files: List[str]
    ) -> ProcessBatchResponse:
        
        return ProcessBatchResponse(
            batch_id=batch.id,
            message="El lote ha sido recibido y está en cola para procesamiento OCR.",
            status=batch.status.value,
            accepted_dnis=accepted_dnis,
            rejected_dnis=rejected_dnis,
            invalid_files=invalid_files
        )

    # Nota: Si en el futuro necesitas convertir el Request en una Entidad antes de 
    # mandarlo al Caso de Uso, aquí agregarías tu método estático:
    # @staticmethod
    # def to_domain(request: ProcessBatchRequest) -> TuEntidad:
    #     pass