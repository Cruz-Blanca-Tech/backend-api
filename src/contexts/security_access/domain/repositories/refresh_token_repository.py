# src/contexts/security_access/domain/repositories/refresh_token_repository.py
from typing import Protocol, Optional
from datetime import datetime
from src.contexts.security_access.domain.value_objects.active_session import ActiveSession

class RefreshTokenRepository(Protocol):
    """
    Contrato (Puerto) para la persistencia de tokens de refresco.
    """
    
    async def save(self, user_id: str, token: str, expires_at: datetime) -> None:
        """Persiste el refresh token para un usuario dado."""
        ...

    # 👇 CAMBIO CRÍTICO AQUÍ
    async def get_session_by_token(self, token: str) -> Optional[ActiveSession]:
        """Recupera la sesión activa completa (ID y caducidad) asociada a un token."""
        ...

    async def delete(self, token: str) -> None:
        """Revoca/Elimina un refresh token específico."""
        ...

    async def delete_all_for_user(self, user_id: str) -> None:
        """Revoca todas las sesiones (tokens) de un usuario."""
        ...