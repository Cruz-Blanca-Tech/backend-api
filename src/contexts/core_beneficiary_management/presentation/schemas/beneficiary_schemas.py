from pydantic import BaseModel
from typing import Optional, List
from datetime import date
from uuid import UUID

from .medical_schemas import MedicalRecordResponse, MedicalRecordPatchRequest
from .education_schemas import EducationRecordResponse, EducationRecordPatchRequest
from .adult_schemas import AdultResponse, AdultPatchRequest
from .historical_document_schemas import HistoricalDocumentResponse

class BeneficiaryResponse(BaseModel):
    id: UUID
    dni: str
    first_name: str
    last_name: str
    birth_date: Optional[date]
    gender: Optional[str]
    is_active: bool
    medical: Optional[MedicalRecordResponse]
    education: Optional[EducationRecordResponse]
    related_adults: List[AdultResponse]
    historical_documents: List[HistoricalDocumentResponse]

class BeneficiarySummaryResponse(BaseModel):
    id: UUID
    dni: str
    first_name: str
    last_name: str
    birth_date: Optional[date]
    age: Optional[int] = None
    gender: Optional[str]
    is_active: bool
    grade: Optional[str] = None

class PaginatedBeneficiaryResponse(BaseModel):
    items: List[BeneficiarySummaryResponse]
    total: int
    skip: int
    limit: int

class BeneficiaryPatchRequest(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    birth_date: Optional[date] = None
    gender: Optional[str] = None
    is_active: Optional[bool] = None
    medical: Optional[MedicalRecordPatchRequest] = None
    education: Optional[EducationRecordPatchRequest] = None
    related_adults: Optional[List[AdultPatchRequest]] = None
