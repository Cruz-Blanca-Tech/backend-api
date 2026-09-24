from typing import Optional, Any
from pydantic import BaseModel, Field, model_validator

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

    @model_validator(mode='before')
    @classmethod
    def flatten_confidence_objects(cls, data: Any) -> Any:
        if isinstance(data, dict):
            flattened = {}
            for key, val in data.items():
                if isinstance(val, dict) and "value" in val:
                    extracted_val = val["value"]
                else:
                    extracted_val = val
                
                if extracted_val is not None and not isinstance(extracted_val, (list, dict)):
                    flattened[key] = str(extracted_val)
                else:
                    flattened[key] = extracted_val
                    
            return flattened
        return data
