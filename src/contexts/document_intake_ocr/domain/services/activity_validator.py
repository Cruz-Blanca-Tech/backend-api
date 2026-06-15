from typing import List
from uuid import UUID
from src.contexts.document_intake_ocr.domain.entities.document_type import DocumentTypeConfig
from src.contexts.document_intake_ocr.domain.repositories.program_repository import ProgramRepository
from src.contexts.document_intake_ocr.domain.repositories.document_catalog_repository import DocumentCatalogRepository
from src.core.validators.exceptions import DomainValidationError, EntityNotFoundException

class ActivityValidator:
    def __init__(self, program_repo: ProgramRepository, catalog_repo: DocumentCatalogRepository):
        self.program_repo = program_repo
        self.catalog_repo = catalog_repo

    async def resolve_and_validate(
        self, 
        program_id: UUID, 
        catalog_ids: List[UUID]
    ) -> List[DocumentTypeConfig]:
        """
        No solo valida la existencia, sino que retorna las entidades resueltas
        para ser inyectadas directamente en el Mapper.
        """
        # 1. Validar Programa
        program = await self.program_repo.get_by_id(program_id)
        if not program:
            raise EntityNotFoundException(f"El programa {program_id} no existe.")

        if not catalog_ids:
            return []

        # 2. Obtener y Validar Catálogo
        existing_configs = await self.catalog_repo.get_by_ids(catalog_ids)
        
        if len(existing_configs) != len(catalog_ids):
            raise DomainValidationError("Uno o más tipos de documentos requeridos no existen.")

        return existing_configs