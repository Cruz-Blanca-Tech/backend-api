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
class ProcessBatchResponse(BaseModel):
    batch_id: UUID = Field(..., description="ID interno del lote creado para hacer seguimiento (Tracking)")
    message: str = Field(..., description="Mensaje de éxito para mostrar al usuario")
    status: str = Field(..., description="Estado inicial del lote (ej. PENDING)")
    accepted_dnis: List[str] = Field(default_factory=list, description="DNIs que pasaron la validación y van al OCR")
    rejected_dnis: List[str] = Field(default_factory=list, description="DNIs incompletos que fueron rebotados")
    invalid_files: List[str] = Field(default_factory=list, description="Archivos que no cumplen el estándar de nombre")