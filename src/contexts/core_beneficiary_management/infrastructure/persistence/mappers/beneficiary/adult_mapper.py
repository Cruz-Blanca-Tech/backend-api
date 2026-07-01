from typing import Optional
from src.contexts.core_beneficiary_management.domain.entities.adult import Adult
from src.contexts.core_beneficiary_management.domain.value_objects.relationship_role import RelationshipRole
from src.contexts.core_beneficiary_management.domain.value_objects.phone import Phone
from src.contexts.core_beneficiary_management.domain.value_objects.dni import DNI
from src.contexts.core_beneficiary_management.domain.value_objects.gender import Gender
from src.contexts.core_beneficiary_management.infrastructure.persistence.model.adult_model import AdultModel

class AdultMapper:
    @staticmethod
    def to_domain(model: Optional[AdultModel]) -> Optional[Adult]:
        if not model:
            return None
            
        try:
            role_enum = RelationshipRole(model.role)
        except ValueError:
            role_enum = RelationshipRole.OTHER

        phone = None
        if model.phone:
            try:
                phone = Phone(model.phone)
            except ValueError:
                pass
                
        gender = None
        if model.gender:
            try:
                gender = Gender(model.gender)
            except ValueError:
                pass
                
        try:
            dni = DNI(model.dni)
        except ValueError:
            dni = DNI("00000000") # Fallback if corrupted

        return Adult(
            id=model.id,
            dni=dni,
            first_name=model.first_name,
            last_name=model.last_name,
            birth_date=model.birth_date,
            gender=gender,
            beneficiary_id=model.beneficiary_id,
            role=role_enum,
            phone=phone,
            is_emergency_contact=model.is_emergency_contact
        )

    @staticmethod
    def to_persistence(entity: Optional[Adult], beneficiary_id) -> Optional[AdultModel]:
        if not entity:
            return None
            
        return AdultModel(
            id=entity.id,
            dni=entity.dni.value if entity.dni else "",
            first_name=entity.first_name,
            last_name=entity.last_name,
            birth_date=entity.birth_date,
            gender=entity.gender.value if entity.gender else None,
            beneficiary_id=beneficiary_id,
            role=entity.role.value,
            phone=entity.phone.value if entity.phone else None,
            is_emergency_contact=entity.is_emergency_contact
        )
