from typing import Optional, List
from pydantic import BaseModel, Field

class RelatedAdultSchema(BaseModel):
    relationship: str
    dni: Optional[str] = None
    full_name: Optional[str] = None
    phone: Optional[str] = None

    class Config:
        from_attributes = True

class FamilySchema(BaseModel):
    adults: List[RelatedAdultSchema] = Field(default_factory=list)
    guardian_dni: Optional[str] = None
    emergency_contact_dni: Optional[str] = None
    validation_issues: List[str] = Field(default_factory=list)

    class Config:
        from_attributes = True
