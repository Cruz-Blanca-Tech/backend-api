from pydantic import BaseModel
from typing import Optional, List

class MedicalRecordResponse(BaseModel):
    has_been_hospitalized: bool
    hospitalization_reason: Optional[str]
    has_been_operated: bool
    operation_reason: Optional[str]
    vaccines: List[str]
    medications: List[str]
    allergies: List[str]
    diseases: List[str]
    insurance: List[str]

class MedicalRecordPatchRequest(BaseModel):
    has_been_hospitalized: Optional[bool] = None
    hospitalization_reason: Optional[str] = None
    has_been_operated: Optional[bool] = None
    operation_reason: Optional[str] = None
    vaccines: Optional[List[str]] = None
    medications: Optional[List[str]] = None
    allergies: Optional[List[str]] = None
    diseases: Optional[List[str]] = None
    insurance: Optional[List[str]] = None
