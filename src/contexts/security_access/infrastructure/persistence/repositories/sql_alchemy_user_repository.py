# src/contexts/security_access/infrastructure/repositories/sql_alchemy_user_repository.py

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
        # Merge hace el "upsert" automáticamente
        await self.session.merge(user_model)
        await self.session.commit()

    async def get_by_email(self, email: str) -> User | None:
        query = select(UserModel).where(UserModel.email == str(email))
        result = await self.session.execute(query)
        user_model = result.scalar_one_or_none()
        
        # Si existe, lo convertimos a entidad de dominio antes de retornarlo
        if user_model:
            return UserMapper.to_domain(user_model)
        return None