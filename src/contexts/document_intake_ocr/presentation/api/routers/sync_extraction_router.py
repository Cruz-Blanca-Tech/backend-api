from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional

from src.contexts.document_intake_ocr.application.schemas.file_item_schema import FileItemSchema
from src.contexts.document_intake_ocr.domain.value_objects.file_item import FileItem
from src.contexts.document_intake_ocr.infrastructure.dependencies.batch_deps import get_storage_adapter, get_extractor_adapter
from src.contexts.security_access.domain.value_objects.token_claims import TokenClaims
from src.contexts.security_access.infrastructure.dependencies import get_current_user
from src.core.config import settings

router = APIRouter(prefix="/api/v1/sync-extract", tags=["Sync Extraction"])

class SyncExtractRequest(BaseModel):
    file: FileItemSchema
    model_id: Optional[str] = None 

class SyncExtractResponse(BaseModel):
    fields: Dict[str, Any]
    confidence: float

@router.post("", response_model=SyncExtractResponse, summary="Procesa un documento en tiempo real y devuelve la data extraída")
async def extract_document_sync(
    request: SyncExtractRequest,
    current_user: TokenClaims = Depends(get_current_user),
    storage = Depends(get_storage_adapter),
    extractor = Depends(get_extractor_adapter)
):
    try:
        model_id_to_use = request.model_id or settings.AZURE_CUSTOM_MODEL_ID
        
        file_item = FileItem(file_id=request.file.source_id, file_name=request.file.file_name)
        file_bytes = await storage.download_file(file_item, current_user.email.value)
        
        ocr_result = await extractor.extract_data(file_bytes, model_id_to_use)
        
        return SyncExtractResponse(
            fields=ocr_result.get("fields", {}),
            confidence=ocr_result.get("confidence", 0.0)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en extraccion sincrona: {str(e)}")
