# src/contexts/security_access/infrastructure/persistence/repositories/sql_refresh_token_repository.py

from datetime import datetime
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import UUID, delete

from src.contexts.security_access.domain.repositories.refresh_token_repository import RefreshTokenRepository
from src.contexts.security_access.domain.value_objects.active_session import ActiveSession
from src.contexts.security_access.infrastructure.persistence.models.refresh_token_model import RefreshTokenModel

class SqlRefreshTokenRepository(RefreshTokenRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    # YA NO TIENE _hash_token. El servicio se encarga de eso.

    async def save(self, user_id: UUID, token_hash: str, expires_at: datetime) -> None:
        # Recibe el hash directamente
        await self.session.execute(
            delete(RefreshTokenModel).where(RefreshTokenModel.user_id == user_id)
        )
        new_token = RefreshTokenModel(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at
        )
        self.session.add(new_token)
        await self.session.commit()

    async def get_session_by_token(self, token_hash: str) -> Optional[ActiveSession]:
        # Busca usando el hash que le pasan
        query = select(RefreshTokenModel).where(
            RefreshTokenModel.token_hash == token_hash,
            RefreshTokenModel.expires_at > datetime.utcnow()
        )
        result = await self.session.execute(query)
        token_record = result.scalars().first()
        
        if token_record:
            return ActiveSession(user_id=str(token_record.user_id), expires_at=token_record.expires_at)
        return None

    async def delete(self, token_hash: str) -> None:
        query = delete(RefreshTokenModel).where(RefreshTokenModel.token_hash == token_hash)
        await self.session.execute(query)
        await self.session.commit()