

from uuid import uuid4

from src.contexts.document_intake_ocr.domain.entities.document_type import DocumentTypeConfig
from src.contexts.document_intake_ocr.application.schemas.document_type_config_schema import DocumentTypeConfigCreateRequest, DocumentTypeConfigResponse, DocumentTypeConfigUpdateRequest
from src.contexts.document_intake_ocr.domain.value_objects.document_code import DocumentTypeCode


class DocumentCatalogMapper:
    @staticmethod
    def to_domain(request: DocumentTypeConfigCreateRequest) -> DocumentTypeConfig:
        return DocumentTypeConfig(
            id=uuid4(), 
            code=DocumentTypeCode(request.code),
            name=request.name,
            year=request.year,
            model_id=request.model_id,
            version=request.version,
            preview_image_url=request.preview_image_url,
            is_active=request.is_active
        )

    @staticmethod
    def to_response(entity: DocumentTypeConfig) -> DocumentTypeConfigResponse:
        print(entity.code)
        print(" ", entity.code.code)
        return DocumentTypeConfigResponse(
            id=entity.id,
            code=entity.code.code,
            name=entity.name,
            year=entity.year,
            model_id=entity.model_id,
            version=entity.version,
            preview_image_url=entity.preview_image_url,
            is_active=entity.is_active
        )

    @staticmethod
    def update_from_request(entity: DocumentTypeConfig, request: DocumentTypeConfigUpdateRequest) -> DocumentTypeConfig:
        update_data = request.model_dump(exclude_unset=True)
        
        for key, value in update_data.items():
            if hasattr(entity, key):
                # Validamos si la propiedad a actualizar es nuestro Value Object
                if key == "code" and value is not None:
                    setattr(entity, key, DocumentTypeCode(value))
                else:
                    setattr(entity, key, value)
        return entity