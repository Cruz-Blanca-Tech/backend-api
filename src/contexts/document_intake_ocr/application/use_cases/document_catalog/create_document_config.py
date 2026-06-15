from src.contexts.document_intake_ocr.application.schemas.document_type_config_schema import DocumentTypeConfigCreateRequest, DocumentTypeConfigResponse
from src.contexts.document_intake_ocr.domain.repositories.document_catalog_repository import DocumentCatalogRepository
from src.contexts.document_intake_ocr.application.mappers.document_catalog_mapper import DocumentCatalogMapper

class CreateDocumentConfigUseCase:
    def __init__(self, repository: DocumentCatalogRepository):
        self.repository = repository

    async def execute(self, request: DocumentTypeConfigCreateRequest) -> DocumentTypeConfigResponse:
        # 1. Mapeamos la petición validada a nuestra entidad pura de negocio
        entity = DocumentCatalogMapper.to_domain(request)
        
        # 2. Persistimos (el repositorio se encarga del INSERT y de recuperar el ID generado)
        await self.repository.save(entity)
        
        # 3. Mapeamos la entidad (ahora con ID) a la respuesta de la API
        return DocumentCatalogMapper.to_response(entity)