from typing import List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.contexts.security_access.domain.entities.user import User
from src.contexts.security_access.infrastructure.persistence.mapper.user_mapper import UserMapper
from src.contexts.security_access.infrastructure.persistence.models.user_model import UserModel

class SqlAlchemyUserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def save(self, user: User) -> None:
        user_model = UserMapper.to_infra(user)
        # Merge hace el "upsert" automáticamente (Inserta si es nuevo, actualiza si ya existe)
        await self.session.merge(user_model)
        await self.session.commit()

    async def get_by_email(self, email: str) -> User | None:
        query = select(UserModel).where(UserModel.email == email)
        result = await self.session.execute(query)
        user_model = result.scalar_one_or_none()
        
        # Si existe, lo convertimos a entidad de dominio antes de retornarlo
        if user_model:
            return UserMapper.to_domain(user_model)
        return None

    async def get_by_id(self, user_id: UUID) -> User | None:
        """Busca un usuario por su ID (UUID) único."""
        query = select(UserModel).where(UserModel.id == user_id)
        result = await self.session.execute(query)
        user_model = result.scalar_one_or_none()
        
        if user_model:
            return UserMapper.to_domain(user_model)
        return None

    async def get_all(self) -> List[User]:
        """Obtiene la lista de todos los usuarios registrados en la base de datos."""
        query = select(UserModel)
        result = await self.session.execute(query)
        # scalars().all() nos devuelve una lista limpia de instancias UserModel
        user_models = result.scalars().all()
        
        # Mapeamos la lista de modelos de infraestructura a entidades de Dominio
        return [UserMapper.to_domain(model) for model in user_models]