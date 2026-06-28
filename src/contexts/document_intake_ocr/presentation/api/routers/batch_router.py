# src/contexts/document_intake_ocr/presentation/api/batch_router.py

from fastapi import APIRouter, BackgroundTasks, Depends

from src.contexts.document_intake_ocr.application.schemas.batch_schema import ProcessBatchRequest, ProcessBatchResponse
from src.contexts.document_intake_ocr.application.use_cases.process_batch.process_batch import ProcessBatchUseCase
from src.contexts.document_intake_ocr.application.schemas.document_query_schema import GetDocumentsByDossierResponse
from src.contexts.document_intake_ocr.application.use_cases.get_documents_by_dossier_use_case import GetDocumentsByDossierUseCase
from src.contexts.document_intake_ocr.infrastructure.dependencies.batch_deps import get_process_batch_use_case, get_documents_by_dossier_use_case
from uuid import UUID

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
