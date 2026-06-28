from dataclasses import dataclass
from typing import Optional

@dataclass
class EducationData:
    school: Optional[str] = None
    grade: Optional[str] = None
    knows_read: bool = False
    knows_write: bool = False
    repeated_grade: bool = False
    learning_difficulties: bool = False

