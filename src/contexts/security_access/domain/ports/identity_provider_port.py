# src/contexts/security_access/domain/ports/identity_provider.py
from typing import Protocol
from src.contexts.security_access.domain.entities.external_user_identity import ExternalUserIdentity

class IdentityProviderPort(Protocol):
    def verify_token(self, token: str) -> ExternalUserIdentity:
        """Verifica el token y retorna un usuario autenticado común."""
        ...