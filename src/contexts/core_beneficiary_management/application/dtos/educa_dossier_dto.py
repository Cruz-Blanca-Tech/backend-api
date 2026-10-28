from typing import List, Optional, Any
from pydantic import BaseModel, Field, model_validator

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

    @model_validator(mode="before")
    @classmethod
    def map_triage_education_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # Mapear campos desde el formato de triaje (knows_read, knows_write, etc.)
            # al formato MDM / Ficha Maestra (knows_how_to_read, knows_how_to_write, etc.)
            if "knows_read" in data and "knows_how_to_read" not in data:
                val = data.get("knows_read")
                data["knows_how_to_read"] = bool(val) if val is not None else False
            if "knows_write" in data and "knows_how_to_write" not in data:
                val = data.get("knows_write")
                data["knows_how_to_write"] = bool(val) if val is not None else False
            if "repeated_grade" in data and "has_repeated_grade" not in data:
                val = data.get("repeated_grade")
                data["has_repeated_grade"] = bool(val) if val is not None else False
            if "learning_difficulties" in data and "has_learning_difficulties" not in data:
                val = data.get("learning_difficulties")
                data["has_learning_difficulties"] = bool(val) if val is not None else False
        return data

class EducaAdultDTO(BaseModel):
    dni: str = ""
    full_name: str = ""
    relationship: str = "OTHER"
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
