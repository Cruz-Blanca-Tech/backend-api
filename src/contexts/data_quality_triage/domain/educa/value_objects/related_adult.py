from dataclasses import dataclass
from typing import Optional

@dataclass
class RelatedAdult:
    relationship: str  # e.g., "FATHER", "MOTHER", "OTHER"
    dni: Optional[str] = None
    full_name: Optional[str] = None
    phone: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "relationship": self.relationship,
            "dni": self.dni,
            "full_name": self.full_name,
            "phone": self.phone
        }
