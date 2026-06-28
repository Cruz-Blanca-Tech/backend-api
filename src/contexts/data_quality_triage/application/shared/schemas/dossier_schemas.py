from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

class DossierRequest(BaseModel):
    """
    Contrato base para cualquier petición de creación o edición de Dossier.
    """
    pass

class DossierResponse(BaseModel):
    """
    Respuesta unificada de cualquier operación de Dossier.
    """
    case_id: str
    status: str
    is_valid: bool
    issues: list[str] = Field(default_factory=list)



