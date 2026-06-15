
from src.contexts.document_intake_ocr.domain.entities.document_type import DocumentTypeConfig
from src.contexts.document_intake_ocr.domain.value_objects.document_code import DocumentTypeCode
from src.contexts.document_intake_ocr.infrastructure.persistence.model.document_type_config import DocumentTypeConfigModel


class DocumentCatalogMapper:
    """
    Traduce exclusivamente el Catálogo Maestro de Documentos entre la BD y el Dominio.
    """
    @staticmethod
    def to_domain(model: DocumentTypeConfigModel) -> DocumentTypeConfig:
        return DocumentTypeConfig(
            id=model.id,
            code=DocumentTypeCode(model.code),
            name=model.name,
            year=model.year,
            model_id=model.model_id,
            version=model.version,
            preview_image_url=model.preview_image_url,
            is_active=model.is_active
        )

    @staticmethod
    def to_model(entity: DocumentTypeConfig) -> DocumentTypeConfigModel:
        # El id no se pasa al instanciar si es None, Postgres lo auto-incrementará.
        return DocumentTypeConfigModel(
            id=entity.id,
            code=str(entity.code),
            name=entity.name,
            year=entity.year,
            model_id=entity.model_id,
            version=entity.version,
            preview_image_url=entity.preview_image_url,
            is_active=entity.is_active
        )