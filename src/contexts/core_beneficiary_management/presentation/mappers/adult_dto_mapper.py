from typing import Optional, List
from src.contexts.core_beneficiary_management.domain.entities.adult import Adult
from src.contexts.core_beneficiary_management.domain.value_objects.dni import DNI
from src.contexts.core_beneficiary_management.domain.value_objects.relationship_role import RelationshipRole
from src.contexts.core_beneficiary_management.domain.value_objects.phone import Phone
from src.contexts.core_beneficiary_management.domain.value_objects.gender import Gender
from src.contexts.core_beneficiary_management.presentation.schemas.adult_schemas import (
    AdultResponse, AdultPatchRequest, AdultCreateRequest
)
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
            phone=domain_entity.phone.value if domain_entity.phone else None,
            is_emergency_contact=domain_entity.is_emergency_contact
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

    @staticmethod
    def from_create_request_list(beneficiary_id: uuid.UUID, create_requests: Optional[List[AdultCreateRequest]]) -> List[Adult]:
        if not create_requests:
            return []
        adults = []
        for req in create_requests:
            try:
                gender = Gender(req.gender.upper()) if req.gender else None
            except ValueError:
                gender = None
            try:
                role = RelationshipRole(req.role.upper()) if req.role else RelationshipRole.OTHER
            except ValueError:
                role = RelationshipRole.OTHER
            try:
                phone = Phone(req.phone) if req.phone else None
            except ValueError:
                phone = None
            try:
                dni = DNI(req.dni) if req.dni else DNI("00000000")
            except ValueError:
                dni = DNI("00000000")
            adults.append(Adult(
                id=req.id or uuid.uuid4(),
                dni=dni,
                first_name=req.first_name,
                last_name=req.last_name,
                birth_date=req.birth_date,
                gender=gender,
                beneficiary_id=beneficiary_id,
                role=role,
                phone=phone,
                is_emergency_contact=req.is_emergency_contact
            ))
        return adults

