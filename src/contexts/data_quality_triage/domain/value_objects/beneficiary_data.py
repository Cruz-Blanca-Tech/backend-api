from dataclasses import dataclass, field
from typing import Optional, List

@dataclass
class BeneficiaryData:
    dni: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    birth_date: Optional[str] = None
    gender: Optional[str] = None
    age: Optional[int] = None
    validation_issues: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "dni": self.dni,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "birth_date": self.birth_date,
            "gender": self.gender,
            "age": self.age,
            "validation_issues": self.validation_issues
        }
