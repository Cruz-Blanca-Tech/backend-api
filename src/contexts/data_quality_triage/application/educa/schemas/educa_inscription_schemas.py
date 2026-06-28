from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List

from src.contexts.data_quality_triage.application.shared.schemas.dossier_schemas import DossierRequest, DossierResponse
from src.contexts.data_quality_triage.application.shared.schemas.triage_schemas import TriageCaseDetailResponse, DiscrepancySchema
from .beneficiary_schemas import BeneficiarySchema
from .family_schemas import FamilySchema
from .education_schemas import EducationSchema
from .medical_schemas import MedicalSchema

class EducaInscriptionData(BaseModel):
    """Esquema para serializar la data del Dossier (EducaInscriptionDossier)."""
    beneficiary: BeneficiarySchema = Field(default_factory=BeneficiarySchema)
    related_adults: FamilySchema = Field(default_factory=FamilySchema)
    education: EducationSchema = Field(default_factory=EducationSchema)
    medical: MedicalSchema = Field(default_factory=MedicalSchema)

    class Config:
        from_attributes = True

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
    domain_data: Optional[EducaInscriptionData] = None

class EducaTriageCasePreviewResponse(BaseModel):
    """
    Respuesta simplificada para la vista previa en el Frontend.
    """
    status: str
    dossier_data: EducaInscriptionData
    discrepancies: List[DiscrepancySchema]

class EducaTriageCaseDetailResponse(BaseModel):
    """
    Respuesta detallada fuertemente tipada para el Triage de Educa.
    """
    id: str
    batch_id: str
    dni_reference: str
    status: str
    verdict: str
    confidence_scores: Dict[str, float]
    dossier_data: EducaInscriptionData
    discrepancies: List[DiscrepancySchema]
