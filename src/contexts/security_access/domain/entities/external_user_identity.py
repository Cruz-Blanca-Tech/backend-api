# src/contexts/security_access/domain/entities/external_identity.py
from dataclasses import dataclass
from src.contexts.security_access.domain.value_objects.email import Email

@dataclass(frozen=True)
class ExternalUserIdentity:
    email: Email
    full_name: str
    picture_url: str

    def __post_init__(self):
        if not self.email:
            raise ValueError("El email es obligatorio para la identidad externa")