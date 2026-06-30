from dataclasses import dataclass
from typing import List, Optional
from uuid import UUID

@dataclass
class MedicalRecord:
    id: UUID
    beneficiary_id: UUID
    has_been_hospitalized: bool
    hospitalization_reason: Optional[str]
    has_been_operated: bool
    operation_reason: Optional[str]
    vaccines: List[str]
    medications: List[str]
    allergies: List[str]
    diseases: List[str]
    insurance: List[str]
