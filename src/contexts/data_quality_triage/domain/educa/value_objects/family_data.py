from dataclasses import dataclass, field
from typing import Optional, List
from src.contexts.data_quality_triage.domain.educa.value_objects.related_adult import RelatedAdult

@dataclass
class FamilyData:
    adults: List[RelatedAdult] = field(default_factory=list)
    guardian_dni: Optional[str] = None
    validation_issues: List[str] = field(default_factory=list)


