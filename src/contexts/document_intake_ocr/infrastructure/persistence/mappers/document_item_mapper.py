from uuid import UUID

from src.contexts.document_intake_ocr.domain.entities.document import DocumentItem, DocumentStatus
from src.contexts.document_intake_ocr.domain.value_objects.dni import DNI
from src.contexts.document_intake_ocr.domain.value_objects.document_code import DocumentTypeCode
from src.contexts.document_intake_ocr.infrastructure.persistence.model.document_item_model import DocumentItemModel


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
        return DocumentItemModel(
            id=entity.id,
            batch_id=batch_id,
            code = entity.document_code.code,  # Llave foránea inyectada
            source_id=entity.source_id,       # <-- CAMBIO: Enlace de origen
            custody_id=entity.custody_id,     # <-- NUEVO: Enlace de custodia final
            file_name=entity.file_name,
            dni_reference=entity.dni_reference.value,
            document_type_config_id=entity.document_type_config_id,
            status=entity.status.value,
            extracted_data=entity.extracted_data,
            confidence_score=entity.confidence_score,
            failure_reason=entity.failure_reason,
            processed_at=entity.processed_at
        )

    @staticmethod
    def to_domain(model: DocumentItemModel) -> DocumentItem:
        return DocumentItem(
            id=model.id,
            source_id=model.source_id,
            document_code= DocumentTypeCode(model.code),      # <-- CAMBIO
            custody_id=model.custody_id,      # <-- NUEVO
            file_name=model.file_name,
            dni_reference=DNI(model.dni_reference),
            document_type_config_id=model.document_type_config_id,
            status=DocumentStatus(model.status),
            extracted_data=model.extracted_data,
            confidence_score=model.confidence_score,
            failure_reason=model.failure_reason,
            processed_at=model.processed_at
        )