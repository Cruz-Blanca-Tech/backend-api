from fastapi import Depends

# 1. Infraestructura (Repositorio)
from asd import get_async_db
from src.contexts.document_intake_ocr.infrastructure.persistence.repositories.sql_catalog_repository import SqlDocumentCatalogRepository

# 2. Aplicación (Casos de Uso)
from src.contexts.document_intake_ocr.application.use_cases.document_catalog.create_document_config import CreateDocumentConfigUseCase
from src.contexts.document_intake_ocr.application.use_cases.document_catalog.update_document_config import UpdateDocumentConfigUseCase
from src.contexts.document_intake_ocr.application.use_cases.document_catalog.list_document_catalog import ListDocumentCatalogUseCase

# --- PROVEEDOR BASE ---
def get_document_catalog_repository(db= Depends(get_async_db))  -> SqlDocumentCatalogRepository:
    """
    Instancia el repositorio del Catálogo de Documentos.
    """
    return SqlDocumentCatalogRepository(db)

# --- PROVEEDORES DE CASOS DE USO ---
def get_create_document_config_use_case(
    repo: SqlDocumentCatalogRepository = Depends(get_document_catalog_repository),
) -> CreateDocumentConfigUseCase:
    return CreateDocumentConfigUseCase(repository=repo)

def get_update_document_config_use_case(
    repo: SqlDocumentCatalogRepository = Depends(get_document_catalog_repository)
) -> UpdateDocumentConfigUseCase:
    return UpdateDocumentConfigUseCase(repository=repo)

def get_list_document_catalog_use_case(
    repo: SqlDocumentCatalogRepository = Depends(get_document_catalog_repository)
) -> ListDocumentCatalogUseCase:
    return ListDocumentCatalogUseCase(repository=repo)