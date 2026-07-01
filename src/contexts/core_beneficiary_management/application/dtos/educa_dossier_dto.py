from typing import List, Optional
from pydantic import BaseModel, Field

class EducaBeneficiaryDTO(BaseModel):
    dni: str
    first_name: str
    last_name: str
    birth_date: Optional[str] = None
    gender: str = "UNKNOWN"
    address: Optional[str] = None

class EducaReligionDTO(BaseModel):
    baptized: Optional[bool] = None
    first_communion: Optional[bool] = None

class EducaPermissionsDTO(BaseModel):
    haircut_permission: Optional[bool] = None
    medical_exams_permission: Optional[bool] = None

class EducaMedicalDTO(BaseModel):
    has_been_hospitalized: bool = False
    hospitalization_reason: Optional[str] = None
    has_been_operated: bool = False
    operation_reason: Optional[str] = None
    vaccines: List[str] = Field(default_factory=list)
    medications: List[str] = Field(default_factory=list)
    allergies: List[str] = Field(default_factory=list)
    diseases: List[str] = Field(default_factory=list)
    insurance: List[str] = Field(default_factory=list)

class EducaEducationDTO(BaseModel):
    school: Optional[str] = None
    grade: Optional[str] = None
    knows_how_to_read: bool = False
    knows_how_to_write: bool = False
    has_repeated_grade: bool = False
    has_learning_difficulties: bool = False

class EducaAdultDTO(BaseModel):
    dni: str = ""
    full_name: str = ""
    role: str = "OTHER"
    phone: Optional[str] = None

class EducaRelatedAdultsDTO(BaseModel):
    adults: List[EducaAdultDTO] = Field(default_factory=list)
    guardian_dni: Optional[str] = None
    emergency_contact_dni: Optional[str] = None

class EducaDossierDTO(BaseModel):
    beneficiary: EducaBeneficiaryDTO
    religion: EducaReligionDTO = Field(default_factory=EducaReligionDTO)
    permissions: EducaPermissionsDTO = Field(default_factory=EducaPermissionsDTO)
    medical: EducaMedicalDTO = Field(default_factory=EducaMedicalDTO)
    education: EducaEducationDTO = Field(default_factory=EducaEducationDTO)
    related_adults: EducaRelatedAdultsDTO = Field(default_factory=EducaRelatedAdultsDTO)
