from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from src.contexts.data_quality_triage.application.shared.schemas.dossier_schemas import DossierRequest, DossierResponse

class BeneficiarySchema(BaseModel):
    dni: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    birth_date: Optional[str] = None
    gender: Optional[str] = None
    age: Optional[int] = None
    validation_issues: List[str] = Field(default_factory=list)

class RelatedAdultSchema(BaseModel):
    relationship: str
    dni: Optional[str] = None
    full_name: Optional[str] = None
    phone: Optional[str] = None

class FamilySchema(BaseModel):
    adults: List[RelatedAdultSchema] = Field(default_factory=list)
    guardian_dni: Optional[str] = None
    validation_issues: List[str] = Field(default_factory=list)

class EducationSchema(BaseModel):
    school: Optional[str] = None
    grade: Optional[str] = None
    knows_read: bool = False
    knows_write: bool = False
    repeated_grade: bool = False
    learning_difficulties: bool = False

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

class EducaInscriptionRequest(DossierRequest):
    """
    Representa la información consolidada inicial o la edición del frontend.
    Es el modelo de transporte oficial para Educa Inscription.
    """
    beneficiary: BeneficiarySchema = Field(default_factory=BeneficiarySchema)
    related_adults: FamilySchema = Field(default_factory=FamilySchema)
    education: EducationSchema = Field(default_factory=EducationSchema)
    medical: MedicalSchema = Field(default_factory=MedicalSchema)

class EducaInscriptionResponse(DossierResponse):
    """
    Respuesta extendida que puede incluir la representación final de los datos.
    """
    canonical_data: Dict[str, Any] = Field(default_factory=dict)
