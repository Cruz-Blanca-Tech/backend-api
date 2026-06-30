from dataclasses import dataclass
from datetime import date
from typing import Optional
from uuid import UUID

from src.contexts.core_beneficiary_management.domain.value_objects.dni import DNI
from src.contexts.core_beneficiary_management.domain.value_objects.gender import Gender

@dataclass
class Person:
    id: UUID
    dni: DNI
    first_name: str
    last_name: str
    birth_date: Optional[date]
    gender: Optional[Gender]
    type: str  # "beneficiary" or "adult"
