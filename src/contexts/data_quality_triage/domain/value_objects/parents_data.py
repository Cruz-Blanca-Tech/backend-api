from dataclasses import dataclass, field
from typing import Optional, List
from src.contexts.data_quality_triage.domain.value_objects.parent_detail import ParentDetail

@dataclass
class ParentsData:
    father: Optional[ParentDetail] = None
    mother: Optional[ParentDetail] = None
    guardian: Optional[ParentDetail] = None
    apoderado_type: Optional[str] = None
    validation_issues: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "father": self.father.to_dict() if self.father else None,
            "mother": self.mother.to_dict() if self.mother else None,
            "guardian": self.guardian.to_dict() if self.guardian else None,
            "apoderado_type": self.apoderado_type,
            "validation_issues": self.validation_issues
        }
