# src/contexts/document_intake_ocr/presentation/api/batch_router.py

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response

from src.contexts.document_intake_ocr.domain.entities.extraction_batch import BatchStatus
from src.contexts.document_intake_ocr.application.schemas.batch_schema import ProcessBatchRequest, ProcessBatchResponse, ListBatchesRequest, GetBatchesSummaryRequest, ListBatchesResponse, BatchItemSchema
from src.contexts.document_intake_ocr.application.use_cases.process_batch.process_batch import ProcessBatchUseCase
from src.contexts.document_intake_ocr.application.schemas.document_query_schema import GetDocumentsByDossierResponse
from src.contexts.document_intake_ocr.application.use_cases.get_documents_by_dossier_use_case import GetDocumentsByDossierUseCase
from src.contexts.document_intake_ocr.application.use_cases.get_document_image_use_case import GetDocumentImageUseCase
from src.contexts.document_intake_ocr.application.use_cases.list_batches_use_case import ListBatchesUseCase
from src.contexts.document_intake_ocr.application.use_cases.get_batches_summary_use_case import GetBatchesSummaryUseCase
from src.contexts.document_intake_ocr.infrastructure.dependencies.batch_deps import get_process_batch_use_case, get_documents_by_dossier_use_case, get_document_image_use_case, get_list_batches_use_case, get_batches_summary_use_case, get_batch_by_id_use_case
from src.contexts.document_intake_ocr.application.use_cases.get_batch_by_id_use_case import GetBatchByIdUseCase
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

@router.get(
    "/{batch_id}/dossiers/{dni_reference}/documents/{document_id}/image",
    summary="Devuelve los bytes de la imagen de un documento (bóveda de custodia)",
)
async def get_document_image(
    batch_id: UUID,
    dni_reference: str,
    document_id: UUID,
    # Guardia de acceso: estas imágenes son sensibles (documentos de identidad en
    # la bóveda privada), así que exigimos un usuario autenticado. El proxy de Next
    # ya reenvía el Bearer del operador a este endpoint.
    current_user: TokenClaims = Depends(get_current_user),
    use_case: GetDocumentImageUseCase = Depends(get_document_image_use_case),
):
    """
    Descarga la imagen del documento desde la bóveda de Custodia usando las
    credenciales del Robot (cuenta de servicio) y la devuelve como binario.

    Estas imágenes NO son públicas: el frontend no recibe el enlace de Drive, solo
    pide por `document_id` y el backend resuelve el acceso. Responde 404 si el
    documento no pertenece a ese lote/DNI o si aún no tiene copia en custodia.
    """
    image = await use_case.execute(
        batch_id=batch_id, dni_reference=dni_reference, document_id=document_id
    )
    if image is None:
        raise HTTPException(status_code=404, detail="El documento no tiene una imagen en custodia.")
    return Response(
        content=image.content,
        media_type=image.media_type,
        # Privado: es contenido sensible por usuario autenticado, no cacheable en CDN.
        headers={"Cache-Control": "private, max-age=3600"},
    )

@router.get("/", response_model=ListBatchesResponse, summary="Obtiene la lista de lotes y sus estados")
async def list_batches(
    skip: int = 0,
    limit: int = 100,
    program_id: Optional[UUID] = Query(None, description="Filtrar por ID del programa"),
    activity_id: Optional[UUID] = Query(None, description="Filtrar por ID de la actividad"),
    status: Optional[str] = Query(None, description="Filtrar por estado del lote"),
    use_case: ListBatchesUseCase = Depends(get_list_batches_use_case)
):
    request = ListBatchesRequest(
        skip=skip,
        limit=limit,
        program_id=program_id,
        activity_id=activity_id,
        status=status
    )
    return await use_case.execute(request)

@router.get("/statuses", summary="Obtiene la lista de estados de lotes disponibles")
async def get_batch_statuses():
    """Devuelve la lista de estados válidos para los lotes en el OCR."""
    return [s.value for s in BatchStatus]

@router.get("/summary", summary="Obtiene un resumen cuantitativo de lotes agrupados por estado")
async def get_batches_summary(
    program_id: Optional[UUID] = Query(None, description="Filtrar por ID del programa"),
    activity_id: Optional[UUID] = Query(None, description="Filtrar por ID de la actividad"),
    status: Optional[str] = Query(None, description="Filtrar por estado del lote"),
    use_case: GetBatchesSummaryUseCase = Depends(get_batches_summary_use_case)
):
    """Devuelve la cantidad total de lotes existentes agrupados por estado, aplicando filtros opcionales."""
    request = GetBatchesSummaryRequest(program_id=program_id, activity_id=activity_id, status=status)
    return await use_case.execute(request)

@router.get("/{batch_id}", response_model=BatchItemSchema, summary="Obtiene el detalle de un lote específico por ID")
async def get_batch_by_id(
    batch_id: UUID,
    use_case: GetBatchByIdUseCase = Depends(get_batch_by_id_use_case)
):
    """Devuelve los detalles, contadores y métricas de un lote en particular."""
    return await use_case.execute(batch_id=batch_id)
