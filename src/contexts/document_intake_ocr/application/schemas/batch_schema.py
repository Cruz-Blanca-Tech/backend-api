from pydantic import BaseModel, Field
from typing import List
from uuid import UUID

from src.contexts.document_intake_ocr.application.schemas.file_item_schema import FileItemSchema


class ProcessBatchRequest(BaseModel):
    activity_id: UUID = Field(..., description="El ID de la Actividad a la que pertenecen estos documentos")
    files: List[FileItemSchema] = Field(..., description="Lista de archivos seleccionados para procesar")

# ==========================================
# RESPONSE (Lo que devuelve el Backend)
# ==========================================
# src/contexts/document_intake_ocr/application/schemas/batch_schema.py
class FailedDocumentDetail(BaseModel):
    file_name: str
    reason: str

class ProcessBatchResponse(BaseModel):
    """
    Respuesta estructurada para el frontend informando el resultado 
    inmediato del filtro y agrupación antes del OCR asíncrono.
    """
    batch_id: UUID
    batch_status: str
    total_dossiers: int
    total_failed_files: int
    failed_files: List[FailedDocumentDetail]
    message: str