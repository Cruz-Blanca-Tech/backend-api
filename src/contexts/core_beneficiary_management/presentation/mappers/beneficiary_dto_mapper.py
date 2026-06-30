from datetime import date
from typing import Optional
from src.contexts.core_beneficiary_management.domain.entities.beneficiary import Beneficiary
from src.contexts.core_beneficiary_management.domain.value_objects.gender import Gender
from src.contexts.core_beneficiary_management.presentation.schemas.beneficiary_schemas import BeneficiaryResponse, BeneficiaryPatchRequest, BeneficiarySummaryResponse

from .medical_dto_mapper import MedicalDtoMapper
from .education_dto_mapper import EducationDtoMapper
from .adult_dto_mapper import AdultDtoMapper
from .historical_document_dto_mapper import HistoricalDocumentDtoMapper

def calculate_age(birth_date: Optional[date]) -> Optional[int]:
    if not birth_date:
        return None
    today = date.today()
    return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))

class BeneficiaryDtoMapper:
    @staticmethod
    def to_response(domain_entity: Optional[Beneficiary]) -> Optional[BeneficiaryResponse]:
        if not domain_entity:
            return None
            
        return BeneficiaryResponse(
            id=domain_entity.id,
            dni=domain_entity.dni.value if domain_entity.dni else "",
            first_name=domain_entity.first_name,
            last_name=domain_entity.last_name,
            birth_date=domain_entity.birth_date,
            gender=domain_entity.gender.value if domain_entity.gender else None,
            is_active=True,
            medical=MedicalDtoMapper.to_response(domain_entity.medical_record),
            education=EducationDtoMapper.to_response(domain_entity.education_record),
            related_adults=[AdultDtoMapper.to_response(adult) for adult in domain_entity.relatives],
            historical_documents=HistoricalDocumentDtoMapper.to_response_list(domain_entity.historical_documents)
        )

    @staticmethod
    def to_summary_response(domain_entity: Optional[Beneficiary]) -> Optional[BeneficiarySummaryResponse]:
        if not domain_entity:
            return None
            
        grade_str = None
        if domain_entity.education_record and domain_entity.education_record.grade:
            grade_str = domain_entity.education_record.grade.value

        return BeneficiarySummaryResponse(
            id=domain_entity.id,
            dni=domain_entity.dni.value if domain_entity.dni else "",
            first_name=domain_entity.first_name,
            last_name=domain_entity.last_name,
            birth_date=domain_entity.birth_date,
            age=calculate_age(domain_entity.birth_date),
            gender=domain_entity.gender.value if domain_entity.gender else None,
            is_active=True,
            grade=grade_str
        )

    @staticmethod
    def patch_domain(domain_entity: Beneficiary, patch_request: BeneficiaryPatchRequest) -> Beneficiary:
        update_data = patch_request.dict(exclude_unset=True, exclude={"medical", "education", "related_adults"})
        
        for field, value in update_data.items():
            if field == "gender" and value is not None:
                setattr(domain_entity, field, Gender(value))
            else:
                setattr(domain_entity, field, value)
                
        # Handle sub-entities
        if patch_request.medical is not None:
            domain_entity.medical_record = MedicalDtoMapper.patch_domain(
                domain_entity.medical_record, patch_request.medical, domain_entity.id
            )
            
        if patch_request.education is not None:
            domain_entity.education_record = EducationDtoMapper.patch_domain(
                domain_entity.education_record, patch_request.education, domain_entity.id
            )
            
        if patch_request.related_adults is not None:
            domain_entity.relatives = AdultDtoMapper.patch_domain_list(
                domain_entity.relatives, patch_request.related_adults
            )
            
        return domain_entity
