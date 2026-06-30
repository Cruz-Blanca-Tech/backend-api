from typing import Optional, List
from src.contexts.core_beneficiary_management.domain.entities.adult import Adult
from src.contexts.core_beneficiary_management.domain.value_objects.relationship_role import RelationshipRole
from src.contexts.core_beneficiary_management.domain.value_objects.phone import Phone
from src.contexts.core_beneficiary_management.domain.value_objects.gender import Gender
from src.contexts.core_beneficiary_management.presentation.schemas.adult_schemas import AdultResponse, AdultPatchRequest
import uuid

class AdultDtoMapper:
    @staticmethod
    def to_response(domain_entity: Adult) -> AdultResponse:
        return AdultResponse(
            id=domain_entity.id,
            dni=domain_entity.dni.value if domain_entity.dni else "",
            first_name=domain_entity.first_name,
            last_name=domain_entity.last_name,
            birth_date=domain_entity.birth_date,
            gender=domain_entity.gender.value if domain_entity.gender else None,
            role=domain_entity.role.value if domain_entity.role else "",
            phone=domain_entity.phone.value if domain_entity.phone else None
        )

    @staticmethod
    def patch_domain_list(existing_adults: List[Adult], patch_requests: Optional[List[AdultPatchRequest]]) -> List[Adult]:
        if not patch_requests:
            return existing_adults
            
        adult_dict = {a.id: a for a in existing_adults}
        
        for patch in patch_requests:
            if patch.id in adult_dict:
                adult = adult_dict[patch.id]
                update_data = patch.dict(exclude_unset=True)
                # Remove id from update_data so we don't try to overwrite it
                update_data.pop("id", None)
                
                for field, value in update_data.items():
                    if field == "role" and value is not None:
                        setattr(adult, field, RelationshipRole(value))
                    elif field == "gender" and value is not None:
                        setattr(adult, field, Gender(value))
                    elif field == "phone" and value is not None:
                        setattr(adult, field, Phone(value))
                    else:
                        setattr(adult, field, value)
                        
        return list(adult_dict.values())
