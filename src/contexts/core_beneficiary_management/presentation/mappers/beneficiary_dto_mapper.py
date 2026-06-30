from typing import Optional
from src.contexts.core_beneficiary_management.domain.entities.beneficiary import Beneficiary
from src.contexts.core_beneficiary_management.domain.value_objects.gender import Gender
from src.contexts.core_beneficiary_management.presentation.schemas.beneficiary_schemas import BeneficiaryResponse, BeneficiaryPatchRequest

from .medical_dto_mapper import MedicalDtoMapper
from .education_dto_mapper import EducationDtoMapper
from .adult_dto_mapper import AdultDtoMapper
from .historical_document_dto_mapper import HistoricalDocumentDtoMapper

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
            is_active=domain_entity.is_active,
            medical=MedicalDtoMapper.to_response(domain_entity.medical),
            education=EducationDtoMapper.to_response(domain_entity.education),
            related_adults=[AdultDtoMapper.to_response(adult) for adult in domain_entity.related_adults],
            historical_documents=HistoricalDocumentDtoMapper.to_response_list(domain_entity.historical_documents)
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
            domain_entity.medical = MedicalDtoMapper.patch_domain(
                domain_entity.medical, patch_request.medical, domain_entity.id
            )
            
        if patch_request.education is not None:
            domain_entity.education = EducationDtoMapper.patch_domain(
                domain_entity.education, patch_request.education, domain_entity.id
            )
            
        if patch_request.related_adults is not None:
            domain_entity.related_adults = AdultDtoMapper.patch_domain_list(
                domain_entity.related_adults, patch_request.related_adults
            )
            
        return domain_entity
