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
    address: Optional[str] = None
    validation_issues: List[str] = field(default_factory=list)

