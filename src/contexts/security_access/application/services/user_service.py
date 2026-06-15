from uuid import UUID
from src.contexts.security_access.domain.entities.user import User
from src.contexts.security_access.domain.repositories.user_repository import UserRepository
from src.contexts.security_access.domain.value_objects.role import Role

class UserService:
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository

    async def update_role(self, user_id: UUID, new_role: Role) -> User:
        """Modifica el rol de un usuario existente aplicando el guardado asíncrono."""
        # 1. Recuperamos la entidad de dominio
        user = await self.user_repository.get_by_id(user_id)
        
        if not user:
            raise ValueError(f"El usuario con ID {user_id} no existe.")

        # 2. Mutamos el estado (Aplicamos regla de negocio)
        user.role = new_role

        # 3. Persistimos los cambios
        await self.user_repository.save(user)

        return user

    async def list_users(self) -> list[User]:
        """Retorna el listado completo de usuarios registrados en el sistema."""
        # Aquí podrías agregar lógica extra de paginación o filtros en el futuro
        return await self.user_repository.get_all()