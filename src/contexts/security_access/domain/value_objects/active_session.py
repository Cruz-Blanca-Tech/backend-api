from dataclasses import dataclass
from datetime import datetime

@dataclass(frozen=True)
class ActiveSession:
    """
    Value Object / DTO que representa los datos vitales de una 
    sesión recuperada desde la persistencia.
    """
    user_id: str
    expires_at: datetime