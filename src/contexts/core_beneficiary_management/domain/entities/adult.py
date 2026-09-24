from dataclasses import dataclass
from typing import Optional
from uuid import UUID

from src.contexts.core_beneficiary_management.domain.entities.person import Person
from src.contexts.core_beneficiary_management.domain.value_objects.relationship_role import RelationshipRole
from src.contexts.core_beneficiary_management.domain.value_objects.phone import Phone

@dataclass
class Adult(Person):
    role: RelationshipRole = RelationshipRole.OTHER
    phone: Optional[Phone] = None
    is_emergency_contact: bool = False
    is_guardian: bool = False

    def __post_init__(self):
        self.type = "adult"
