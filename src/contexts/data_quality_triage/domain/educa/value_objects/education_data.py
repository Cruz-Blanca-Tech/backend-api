from dataclasses import dataclass, field
from typing import Optional

@dataclass
class EducationData:
    school: Optional[str] = None
    grade: Optional[str] = None
    knows_read: bool = True
    knows_write: bool = True
    repeated_grade: bool = False
    learning_difficulties: Optional[bool] = None
    validation_issues: list = field(default_factory=list)

