from dataclasses import dataclass
from typing import Optional

@dataclass
class DeclarationData:
    day: Optional[str] = None
    month: Optional[str] = None
    year: Optional[str] = None
    child_dni: Optional[str] = None
    child_name: Optional[str] = None
    father_dni: Optional[str] = None
    mother_dni: Optional[str] = None
    father_name: Optional[str] = None
    mother_name: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "day": self.day,
            "month": self.month,
            "year": self.year,
            "child_dni": self.child_dni,
            "child_name": self.child_name,
            "father_dni": self.father_dni,
            "mother_dni": self.mother_dni,
            "father_name": self.father_name,
            "mother_name": self.mother_name
        }
