from typing import Optional, List
from pydantic import BaseModel, Field

class MedicalSchema(BaseModel):
    allergies: List[str] = Field(default_factory=list)
    diseases: List[str] = Field(default_factory=list)
    insurance: List[str] = Field(default_factory=list)
    has_been_operated: bool = False
    operation_reason: Optional[str] = None
    has_been_hospitalized: bool = False
    hospitalization_reason: Optional[str] = None
    has_complete_vaccines: bool = False
    received_tetanus_vaccine: bool = False
    is_taking_medication: bool = False
    medication_name: Optional[str] = None

    class Config:
        from_attributes = True
