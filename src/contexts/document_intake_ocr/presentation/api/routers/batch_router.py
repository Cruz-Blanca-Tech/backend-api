# src/contexts/document_intake_ocr/presentation/api/batch_router.py

from fastapi import APIRouter, BackgroundTasks, Depends

from src.contexts.document_intake_ocr.domain.entities.extraction_batch import BatchStatus
from src.contexts.document_intake_ocr.application.schemas.batch_schema import ProcessBatchRequest, ProcessBatchResponse
from src.contexts.document_intake_ocr.application.use_cases.process_batch.process_batch import ProcessBatchUseCase
from src.contexts.document_intake_ocr.application.schemas.document_query_schema import GetDocumentsByDossierResponse
from src.contexts.document_intake_ocr.application.use_cases.get_documents_by_dossier_use_case import GetDocumentsByDossierUseCase
from src.contexts.document_intake_ocr.application.use_cases.list_batches_use_case import ListBatchesUseCase
from src.contexts.document_intake_ocr.infrastructure.dependencies.batch_deps import get_process_batch_use_case, get_documents_by_dossier_use_case, get_list_batches_use_case
from uuid import UUID
from typing import Optional
from fastapi import Query

# Mantenemos el desacoplamiento: importamos solo el modelo de Auth para el tipado
from src.contexts.security_access.domain.value_objects.token_claims import TokenClaims
from src.contexts.security_access.infrastructure.dependencies import get_current_user

router = APIRouter(prefix="/api/v1/batches", tags=["Batch Extractor Process"])

@router.post("/", response_model=ProcessBatchResponse, summary="Inicia el procesamiento masivo de un lote documental")
async def create_batch(
    request: ProcessBatchRequest,
    background_tasks: BackgroundTasks,
    # Inyección de seguridad (el guardia de acceso)
    current_user: TokenClaims = Depends(get_current_user),
    # Inyección del Caso de Uso (el orquestador)
    use_case: ProcessBatchUseCase = Depends(get_process_batch_use_case)
):
    # El Caso de Uso es totalmente agnóstico a la seguridad; recibe datos puros
    response = await use_case.execute(
        request=request,
        user_id=current_user.user_id,
        user_email=current_user.email.value,
        background_tasks=background_tasks
    )
    return response

@router.get("/{batch_id}/dossiers/{dni_reference}/documents", response_model=GetDocumentsByDossierResponse)
async def get_documents_by_dossier(
    batch_id: UUID,
    dni_reference: str,
    use_case: GetDocumentsByDossierUseCase = Depends(get_documents_by_dossier_use_case)
):
    """
    Obtiene los documentos procesados por el OCR pertenecientes a un DNI específico dentro de un lote.
    Retorna la data cruda útil para el frontend (IDs, nombres de archivo y URLs).
    """
    return await use_case.execute(batch_id=batch_id, dni_reference=dni_reference)

@router.get("/", summary="Obtiene la lista de lotes y sus estados")
async def list_batches(
    skip: int = 0,
    limit: int = 100,
    program_id: Optional[UUID] = Query(None, description="Filtrar por ID del programa"),
    activity_id: Optional[UUID] = Query(None, description="Filtrar por ID de la actividad"),
    status: Optional[str] = Query(None, description="Filtrar por estado del lote"),
    use_case: ListBatchesUseCase = Depends(get_list_batches_use_case)
):
    return await use_case.execute(
        skip=skip, 
        limit=limit, 
        program_id=program_id, 
        activity_id=activity_id, 
        status=status
    )

@router.get("/statuses", summary="Obtiene la lista de estados de lotes disponibles")
async def get_batch_statuses():
    """Devuelve la lista de estados válidos para los lotes en el OCR."""
    return [s.value for s in BatchStatus]
