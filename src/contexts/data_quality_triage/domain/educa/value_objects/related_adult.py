from dataclasses import dataclass
from typing import Optional

@dataclass
class RelatedAdult:
    relationship: str  # e.g., "FATHER", "MOTHER", "OTHER"
    dni: Optional[str] = None
    full_name: Optional[str] = None
    phone: Optional[str] = None


