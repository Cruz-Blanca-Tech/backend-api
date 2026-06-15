from typing import Protocol, Optional, List
from uuid import UUID

from src.contexts.security_access.domain.entities.user import User

class UserRepository(Protocol):
    
    async def save(self, user: User) -> None:
        """Persiste o actualiza un usuario en la base de datos."""
        ...

    async def get_by_email(self, email: str) -> Optional[User]:
        """Busca un usuario por su correo electrónico."""
        ...

    async def get_by_id(self, user_id: UUID) -> Optional[User]:
        """Busca un usuario por su ID (UUID) único."""
        ...

    async def get_all(self) -> List[User]:
        """Obtiene la lista de todos los usuarios registrados en el sistema."""
        ...