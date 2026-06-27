from typing import Optional, Dict, Any
from pydantic import BaseModel

class DniRaw(BaseModel):
    """Representa el payload crudo extraído de un DNI (Aplica tanto para DNIAP como para DNIBEF)"""
    DocumentNumber: Optional[str] = None
    FirstName: Optional[str] = None
    LastName: Optional[str] = None
    DateOfBirth: Optional[str] = None
    DateOfExpiration: Optional[str] = None
    Address: Optional[Dict[str, Any]] = None
