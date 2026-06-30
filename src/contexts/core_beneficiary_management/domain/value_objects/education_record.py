from dataclasses import dataclass
from typing import Optional
from uuid import UUID
from src.contexts.core_beneficiary_management.domain.value_objects.grade import Grade

@dataclass
class EducationRecord:
    id: UUID
    beneficiary_id: UUID
    school: Optional[str]
    grade: Optional[Grade]
    knows_how_to_read: bool
    knows_how_to_write: bool
    has_repeated_grade: bool
    has_learning_difficulties: bool
