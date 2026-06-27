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


class EducaInscriptionRequest(DossierRequest):
    """
    Representa la información consolidada inicial o la edición del frontend.
    Es el modelo de transporte oficial para Educa Inscription.
    """
    beneficiary: Dict[str, Any] = Field(default_factory=dict)
    parents: Dict[str, Any] = Field(default_factory=dict)
    education: Dict[str, Any] = Field(default_factory=dict)
    medical: Dict[str, Any] = Field(default_factory=dict)

class EducaInscriptionResponse(DossierResponse):
    """
    Respuesta extendida que puede incluir la representación final de los datos.
    """
    canonical_data: Dict[str, Any] = Field(default_factory=dict)
