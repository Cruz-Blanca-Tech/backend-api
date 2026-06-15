# src/contexts/document_intake_ocr/application/schemas/program_schema.py

from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID

# --- 1. Base Class ---
# Contiene la definición de los campos que son compartidos.
# Los hacemos opcionales para que el 'UpdateRequest' los herede como tal.
class ProgramBase(BaseModel):
    name: Optional[str] = Field(None, min_length=3, max_length=100)
    description: Optional[str] = Field(None, max_length=255)
    is_active: Optional[bool] = True

# --- 2. Request DTOs ---

class ProgramCreateRequest(ProgramBase):
    name: str = Field(..., min_length=3, max_length=100)

class ProgramUpdateRequest(ProgramBase):
    pass

# --- 3. Response DTO ---

class ProgramResponse(BaseModel):
    """Lo que el sistema devuelve al frontend."""
    id: UUID
    name: str
    description: Optional[str]
    is_active: bool

    class Config:
        from_attributes = True