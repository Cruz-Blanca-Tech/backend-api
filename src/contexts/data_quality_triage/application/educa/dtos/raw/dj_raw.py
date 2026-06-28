from typing import Optional
from pydantic import BaseModel, Field

class DjRaw(BaseModel):
    """Representa el payload crudo extraído de la Declaración Jurada (DJ)"""
    child_dni: Optional[str] = Field(default=None, alias="child_dni", title="DNI Niño")
    child_name: Optional[str] = Field(default=None, alias="child_name", title="Nombre Niño")
    declaration_day: Optional[str] = Field(default=None, alias="declaration_day")
    declaration_month: Optional[str] = Field(default=None, alias="declaration_month")
    declaration_year: Optional[str] = Field(default=None, alias="declaration_year")
    parents_father_dni: Optional[str] = Field(default=None, alias="parents_father_dni")
    parents_father_name: Optional[str] = Field(default=None, alias="parents_father_name")
    parents_mother_dni: Optional[str] = Field(default=None, alias="parents_mother_dni")
    parents_mother_name: Optional[str] = Field(default=None, alias="parents_mother_name")
    guardian_dni: Optional[str] = Field(default=None, alias="guardian_dni")

    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)
