from uuid import UUID

from src.contexts.document_intake_ocr.domain.entities.document import DocumentItem, DocumentStatus
from src.contexts.document_intake_ocr.domain.value_objects.group_key import GroupKey
from src.contexts.document_intake_ocr.domain.value_objects.document_code import DocumentTypeCode
from src.contexts.document_intake_ocr.infrastructure.persistence.model.document_item_model import DocumentItemModel
from fastapi.encoders import jsonable_encoder
import logging

logger = logging.getLogger(__name__)

class DocumentItemMapper:
    """
    Mapper exclusivo para aislar la traducción de la entidad DocumentItem
    hacia el modelo de base de datos y viceversa.
    """

    @staticmethod
    def to_model(entity: DocumentItem, batch_id: UUID) -> DocumentItemModel:
        """
        Nota: Recibe el batch_id como parámetro adicional porque en el dominio 
        el hijo no conoce al padre, pero en SQL sí necesitamos la llave foránea.
        """
        code_str = entity.document_code.code if entity.document_code else None

        return DocumentItemModel(
            id=entity.id,
            batch_id=batch_id,
            code = code_str,  # Llave foránea inyectada
            source_id=entity.source_id,       # <-- CAMBIO: Enlace de origen
            custody_id=entity.custody_id,     # <-- NUEVO: Enlace de custodia final
            file_name=entity.file_name,
            dni_reference=entity.dni_reference.value if entity.dni_reference else None,
            document_type_config_id=entity.document_type_config_id,
            status=entity.status.value,
            extracted_data=jsonable_encoder(entity.extracted_data),            
            confidence_score=entity.confidence_score,
            failure_reason=entity.failure_reason,
            processed_at=entity.processed_at
        )

    @staticmethod
    def to_domain(model: DocumentItemModel) -> DocumentItem:

        doc_code = DocumentTypeCode(model.code) if model.code else None
        # Tolerante a propósito: la clave de agrupación no es un DNI validado,
        # así que una fila legacy con un valor no numérico no debe impedir leer
        # el lote entero. Se deja sin clave y `BatchMapper` la manda a
        # rechazados, que es donde puede verse y repararse.
        dni_vo = None
        if model.dni_reference:
            try:
                dni_vo = GroupKey(model.dni_reference)
            except ValueError:
                logger.warning(
                    "DocumentItemMapper: dni_reference '%s' de %s no es una clave "
                    "de agrupación válida; el documento queda sin expediente.",
                    model.dni_reference,
                    model.id,
                )

        return DocumentItem(
            id=model.id,
            source_id=model.source_id,
            document_code= doc_code,      # <-- CAMBIO
            custody_id=model.custody_id,      # <-- NUEVO
            file_name=model.file_name,
            dni_reference=dni_vo,
            document_type_config_id=model.document_type_config_id,
            status=DocumentStatus(model.status),
            extracted_data=model.extracted_data,
            confidence_score=model.confidence_score,
            failure_reason=model.failure_reason,
            processed_at=model.processed_at
        )