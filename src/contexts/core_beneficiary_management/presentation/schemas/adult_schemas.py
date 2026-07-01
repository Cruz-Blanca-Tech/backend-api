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

class AdultPatchRequest(BaseModel):
    id: UUID  # Required to know which adult to update
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    birth_date: Optional[date] = None
    gender: Optional[str] = None
    role: Optional[str] = None
    phone: Optional[str] = None
    is_emergency_contact: Optional[bool] = None
