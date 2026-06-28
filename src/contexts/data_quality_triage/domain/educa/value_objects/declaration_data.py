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
