from pydantic import BaseModel, Field
from typing import List, Optional
from uuid import UUID

# --- 1. Base Class (Shared definitions) ---
# Aquí definimos los campos comunes. 
# Nota: Al usar Optional, no forzamos su envío en el Update.

class ActivityRequirementRequest(BaseModel):
    document_type_config_id: UUID = Field(...) # Obligatorio
    is_required: bool = True
    confidence_threshold: float = Field(0.85, ge=0.0, le=1.0)

class ActivityBase(BaseModel):
    name: Optional[str] = Field(None, min_length=3, max_length=100)
    is_active: Optional[bool] = True
    program_id: Optional[UUID] = None
    requirements: Optional[List[ActivityRequirementRequest]] = None

class ActivityRequirementResponse(BaseModel):
    document_type_config_id: UUID
    is_required: bool
    confidence_threshold: float

# --- 3. Request DTOs (Lo que recibes) ---

class ActivityCreateRequest(ActivityBase):
    """Para crear una actividad nueva. Se heredan los opcionales y se añaden los obligatorios."""
    program_id: UUID = Field(...) # Obligatorio
    name: str = Field(..., min_length=3) # Sobrescribimos para obligar
    requirements: List[ActivityRequirementRequest] # Obligatorio


class ActivityUpdateRequest(ActivityBase):
    """Para actualizar una actividad. Solo envías lo que deseas cambiar."""
    # Como hereda de ActivityBase, name, year e is_active ya son opcionales.
    # Si quisieras permitir actualizar los requerimientos, los añadirías aquí como opcionales.
    pass

# --- 4. Response DTO (Lo que devuelves) ---

class ActivityResponse(BaseModel):
    id: UUID
    program_id: UUID
    name: str
    requirements: List[ActivityRequirementResponse]
    is_active: bool

    class Config:
        from_attributes = True  # Indispensable para convertir modelos de SQLAlchemy