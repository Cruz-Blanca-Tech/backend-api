from typing import Optional, List
from pydantic import BaseModel, Field

class BeneficiarySchema(BaseModel):
    dni: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    birth_date: Optional[str] = None
    gender: Optional[str] = None
    address: Optional[str] = None

    validation_issues: List[str] = Field(default_factory=list)

    class Config:
        from_attributes = True
