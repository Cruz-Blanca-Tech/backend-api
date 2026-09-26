from pydantic import BaseModel
from typing import Optional
from datetime import date
from uuid import UUID

class AdultResponse(BaseModel):
    id: UUID
    dni: str
    first_name: str
    last_name: str
    birth_date: Optional[date]
    gender: Optional[str]
    role: str
    phone: Optional[str]
    is_emergency_contact: bool = False
    is_guardian: bool = False

class AdultPatchRequest(BaseModel):
    """Actualización de un familiar (padre/madre/tutor) del beneficiario.

    SIN `birth_date` a propósito, igual que en el patch del beneficiario: la fecha
    de nacimiento es dato del MAESTRO y se corrige en el MDM, no desde el flujo
    que manda la ficha. Los expedientes tampoco la aportan (ver
    `EducaDossierMapper`: `birth_date=None`), así que aquí no hay nada que
    escribir. La columna sigue existiendo y se devuelve en `AdultResponse`."""

    id: UUID  # Required to know which adult to update
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    gender: Optional[str] = None
    role: Optional[str] = None
    phone: Optional[str] = None
    is_emergency_contact: Optional[bool] = None
    is_guardian: Optional[bool] = None

class AdultCreateRequest(BaseModel):
    """Alta de un familiar. Tampoco lleva `birth_date`: se crea sin ella."""

    id: Optional[UUID] = None
    dni: Optional[str] = None
    first_name: str
    last_name: str
    gender: Optional[str] = None
    role: str = "OTHER"
    phone: Optional[str] = None
    is_emergency_contact: bool = False
    is_guardian: bool = False

