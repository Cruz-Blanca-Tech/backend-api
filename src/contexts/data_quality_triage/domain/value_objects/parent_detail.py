from dataclasses import dataclass
from typing import Optional

@dataclass
class ParentDetail:
    dni: Optional[str] = None
    full_name: Optional[str] = None
    phone: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "dni": self.dni,
            "full_name": self.full_name,
            "phone": self.phone
        }
