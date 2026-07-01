from dataclasses import dataclass, field
from typing import Optional, List

@dataclass
class PermissionsData:
    haircut_permission: Optional[bool] = None
    medical_exams_permission: Optional[bool] = None
    validation_issues: List[str] = field(default_factory=list)
