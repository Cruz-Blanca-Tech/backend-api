from typing import List
from src.contexts.document_intake_ocr.application.schemas.document_type_config_schema import DocumentTypeConfigResponse
from src.contexts.document_intake_ocr.domain.repositories.document_catalog_repository import DocumentCatalogRepository
from src.contexts.document_intake_ocr.application.mappers.document_catalog_mapper import DocumentCatalogMapper

class ListDocumentCatalogUseCase:
    def __init__(self, repository: DocumentCatalogRepository):
        self.repository = repository

    async def execute(self) -> List[DocumentTypeConfigResponse]:
        # Recupera solo los documentos vigentes (is_active=True)
        entities = await self.repository.get_all_active()
        
        # Transforma toda la lista a DTOs de salida en una sola línea elegante
        return [DocumentCatalogMapper.to_response(entity) for entity in entities]