# src/contexts/document_intake_ocr/application/schemas/document_catalog_schema.py

from uuid import UUID

from pydantic import BaseModel, Field
from typing import Optional

# --- 1. Base: Campos comunes a las operaciones ---
# Esto evita repetir la lógica de validación para campos como 'name' o 'version'
class DocumentCatalogBase(BaseModel):
    name: Optional[str] = Field(None, min_length=3, max_length=100, description="Nombre legible del documento")
    model_id: Optional[str] = Field(None, description="ID del modelo en Azure Document Intelligence")
    version: Optional[int] = Field(None, ge=1, description="Versión técnica del modelo")
    preview_image_url: Optional[str] = Field(None, description="URL de la imagen de previsualización")
    is_active: Optional[bool] = Field(None, description="Estado de vigencia del catálogo")
    year: Optional[int] = Field(..., description="Año de vigencia")

# --- 2. Request DTOs ---

class DocumentTypeConfigCreateRequest(DocumentCatalogBase):
    """Contrato para crear un nuevo formato documental (Todos los campos son obligatorios)."""
    # Sobrescribimos los campos de Base para hacerlos obligatorios en la creación
    code: str = Field(..., min_length=2, max_length=10, description="Código único, ej: FINS")
    name: str = Field(..., min_length=3, max_length=100) 
    model_id: str 
    version: int = Field(default=1, ge=1)
    year: int = Field(..., description="Año de vigencia")

class DocumentTypeConfigUpdateRequest(DocumentCatalogBase):
    """Contrato para actualizar un formato (Campos opcionales)."""
    # Al heredar de Base sin definir nada nuevo, todos los campos se mantienen opcionales
    # tal como los definimos en la clase Base.
    pass

# --- 3. Response DTO ---

class DocumentTypeConfigResponse(BaseModel):
    """Contrato de respuesta: Lo que el sistema devuelve tras la operación."""
    id: UUID  # Generado por la base de datos
    code: str
    name: str
    year: int
    model_id: str
    version: int
    preview_image_url: Optional[str]
    is_active: bool

    class Config:
        # Esto permite que Pydantic lea los atributos de objetos de SQLAlchemy
        from_attributes = True