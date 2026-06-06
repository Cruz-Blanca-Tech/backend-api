# src/contexts/auth/domain/repositories/user_repository.py
from typing import Protocol, Optional

from src.contexts.security_access.domain.entities.user import User

class UserRepository(Protocol):
    def save(self, user: User) -> None:
        """Persiste un nuevo usuario en la base de datos."""
        ...

    def get_by_email(self, email: str) -> Optional[User]:
        """Busca un usuario por su correo electrónico."""
        ...