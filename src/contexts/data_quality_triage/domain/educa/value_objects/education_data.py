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

    def to_dict(self) -> dict:
        return {
            "school": self.school,
            "grade": self.grade,
            "knows_read": self.knows_read,
            "knows_write": self.knows_write,
            "repeated_grade": self.repeated_grade,
            "learning_difficulties": self.learning_difficulties
        }
