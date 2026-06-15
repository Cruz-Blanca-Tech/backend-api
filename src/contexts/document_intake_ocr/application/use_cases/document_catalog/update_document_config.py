from src.contexts.document_intake_ocr.application.schemas.document_type_config_schema import DocumentTypeConfigResponse, DocumentTypeConfigUpdateRequest
from src.contexts.document_intake_ocr.domain.repositories.document_catalog_repository import DocumentCatalogRepository
from src.contexts.document_intake_ocr.application.mappers.document_catalog_mapper import DocumentCatalogMapper
from src.core.validators.exceptions import EntityNotFoundException

class UpdateDocumentConfigUseCase:
    def __init__(self, repository: DocumentCatalogRepository):
        self.repository = repository

    async def execute(self, catalog_id: int, request: DocumentTypeConfigUpdateRequest) -> DocumentTypeConfigResponse:
        # 1. Verificamos que el documento exista
        entity = await self.repository.get_by_id(catalog_id)
        if not entity:
            raise EntityNotFoundException(f"El documento con ID {catalog_id} no existe en el catálogo.")

        # 2. Aplicamos las modificaciones dinámicamente
        updated_entity = DocumentCatalogMapper.update_from_request(entity, request)
        
        # 3. Guardamos los cambios
        await self.repository.save(updated_entity)
        
        return DocumentCatalogMapper.to_response(updated_entity)