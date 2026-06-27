from typing import Optional
from pydantic import BaseModel

class DeclaracionJuradaRaw(BaseModel):
    """Representa el payload crudo extraído de la Declaración Jurada (DJ)"""
    child_dni: Optional[str] = None
    child_name: Optional[str] = None
    declaration_day: Optional[str] = None
    declaration_month: Optional[str] = None
    declaration_year: Optional[str] = None
    parents_father_dni: Optional[str] = None
    parents_father_name: Optional[str] = None
    parents_mother_dni: Optional[str] = None
    parents_mother_name: Optional[str] = None
