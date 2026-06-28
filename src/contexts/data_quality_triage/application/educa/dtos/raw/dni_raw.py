from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

class DniRaw(BaseModel):
    """Representa el payload crudo extraído de un DNI (Aplica para DNIAP y DNIBE)"""
    document_number: Optional[str] = Field(default=None, alias="DocumentNumber", title="Número de Documento")
    first_name: Optional[str] = Field(default=None, alias="FirstName", title="Nombres")
    last_name: Optional[str] = Field(default=None, alias="LastName", title="Apellidos")
    date_of_birth: Optional[str] = Field(default=None, alias="DateOfBirth", title="Fecha de Nacimiento")
    date_of_expiration: Optional[str] = Field(default=None, alias="DateOfExpiration", title="Fecha de Expiración")
    address: Optional[Dict[str, Any]] = Field(default=None, alias="Address", title="Dirección")

    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)
