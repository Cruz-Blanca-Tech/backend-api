from pydantic import BaseModel
from typing import Optional, List
from datetime import date
from uuid import UUID

from .medical_schemas import MedicalRecordResponse, MedicalRecordPatchRequest, MedicalRecordCreateRequest
from .education_schemas import EducationRecordResponse, EducationRecordPatchRequest, EducationRecordCreateRequest
from .adult_schemas import AdultResponse, AdultPatchRequest, AdultCreateRequest
from .historical_document_schemas import HistoricalDocumentResponse

class BeneficiaryResponse(BaseModel):
    id: UUID
    dni: str
    first_name: str
    last_name: str
    birth_date: Optional[date]
    gender: Optional[str]
    address: Optional[str]
    baptized: Optional[bool]
    first_communion: Optional[bool]
    haircut_permission: Optional[bool]
    medical_exams_permission: Optional[bool]
    is_active: bool
    medical: Optional[MedicalRecordResponse]
    education: Optional[EducationRecordResponse]
    related_adults: List[AdultResponse]
    historical_documents: List[HistoricalDocumentResponse]

class MdmRelativeSnapshot(BaseModel):
    """Familiar (adulto) del beneficiario en el dato máster, para el triaje."""
    relationship: str
    dni: str
    full_name: str
    phone: Optional[str] = None
    is_emergency_contact: bool = False
    is_guardian: bool = False

class MdmBeneficiarySnapshot(BaseModel):
    """Snapshot de identidad + familiares de un beneficiario YA registrado en el MDM.

    Lo consume la pantalla de corrección de triaje: cuando el DNI del expediente
    coincide con un beneficiario existente, la UI muestra estos valores (los del
    máster son la verdad) y bloquea su edición.
    """
    dni: str
    first_name: str
    last_name: str
    birth_date: Optional[date] = None
    gender: Optional[str] = None
    address: Optional[str] = None
    relatives: List[MdmRelativeSnapshot] = []

class MdmBeneficiaryMatchResponse(BaseModel):
    """Respuesta de GET /beneficiaries/by-dni/{dni}: existe o no en el máster."""
    exists: bool
    beneficiary: Optional[MdmBeneficiarySnapshot] = None

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

class BeneficiaryCreateRequest(BaseModel):
    id: Optional[UUID] = None
    dni: str
    first_name: str
    last_name: str
    birth_date: Optional[date] = None
    gender: Optional[str] = None
    address: Optional[str] = None
    baptized: Optional[bool] = None
    first_communion: Optional[bool] = None
    haircut_permission: Optional[bool] = None
    medical_exams_permission: Optional[bool] = None
    medical: Optional[MedicalRecordCreateRequest] = None
    education: Optional[EducationRecordCreateRequest] = None
    related_adults: Optional[List[AdultCreateRequest]] = None

