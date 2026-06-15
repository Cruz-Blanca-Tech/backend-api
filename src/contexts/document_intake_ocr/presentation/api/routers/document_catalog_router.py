from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List

# Importamos las clases de tipado para los Casos de Uso
from src.contexts.document_intake_ocr.application.schemas.document_type_config_schema import DocumentTypeConfigCreateRequest, DocumentTypeConfigResponse, DocumentTypeConfigUpdateRequest
from src.contexts.document_intake_ocr.application.use_cases.document_catalog.create_document_config import CreateDocumentConfigUseCase
from src.contexts.document_intake_ocr.application.use_cases.document_catalog.update_document_config import UpdateDocumentConfigUseCase
from src.contexts.document_intake_ocr.application.use_cases.document_catalog.list_document_catalog import ListDocumentCatalogUseCase

# IMPORTACIÓN DE ARQUITECTURA: Consumimos la fábrica modular de dependencias
from src.contexts.document_intake_ocr.infrastructure.dependencies.document_catalog_deps import (
    get_create_document_config_use_case,
    get_update_document_config_use_case,
    get_list_document_catalog_use_case
)
from src.contexts.security_access.infrastructure.api.dependencies.policies import ALLOW_ADMIN_ONLY, ALLOW_ANY_STAFF

router = APIRouter(prefix="/document-catalog", tags=["Document Catalog (Azure OCR Models)"])


@router.post("/", response_model=DocumentTypeConfigResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(ALLOW_ADMIN_ONLY)])
async def create_document_config(
    request: DocumentTypeConfigCreateRequest,
    use_case: CreateDocumentConfigUseCase = Depends(get_create_document_config_use_case)
):
    """Registra una nueva plantilla documental y la vincula a un modelo de Azure."""
    return await use_case.execute(request)


@router.patch("/{catalog_id}", response_model=DocumentTypeConfigResponse, dependencies=[Depends(ALLOW_ADMIN_ONLY)])
async def update_document_config(
    catalog_id: UUID,
    request: DocumentTypeConfigUpdateRequest,
    use_case: UpdateDocumentConfigUseCase = Depends(get_update_document_config_use_case)
):
    """Modifica dinámicamente propiedades del catálogo (ID de modelo de IA, versión, etc.)."""
    try:
        return await use_case.execute(catalog_id, request)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/", response_model=List[DocumentTypeConfigResponse], dependencies=[Depends(ALLOW_ANY_STAFF)])
async def list_catalog(use_case: ListDocumentCatalogUseCase = Depends(get_list_document_catalog_use_case)):
    """Retorna los formatos documentales vigentes soportados por el motor de visión artificial."""
    return await use_case.execute()