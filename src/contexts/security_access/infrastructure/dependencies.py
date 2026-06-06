# src/contexts/auth/infrastructure/dependencies.py
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.contexts.security_access.application.policies.auth_policies import DomainRestrictionPolicy
from src.contexts.security_access.application.services.auth_service import AuthService
from src.contexts.security_access.infrastructure.mapper.token_mapper import TokenMapper
from src.contexts.security_access.infrastructure.repositories.sql_alchemy_user_repository import SqlAlchemyUserRepository
from src.contexts.security_access.infrastructure.repositories.sql_alchemy_token_refresh import SqlRefreshTokenRepository
from src.contexts.security_access.infrastructure.adapters.google_auth_adapter import GoogleIdentityAdapter
from src.contexts.security_access.infrastructure.security.jwt_token_provider import JwtTokenProvider
from src.core.database import get_async_db
from src.core.config import settings 

def get_auth_service(db: AsyncSession = Depends(get_async_db)) -> AuthService:
    adapter = GoogleIdentityAdapter(client_id=settings.GOOGLE_CLIENT_ID)
    user_repo = SqlAlchemyUserRepository(db)
    token_repo = SqlRefreshTokenRepository(db)
    token_mapper = JwtTokenProvider(settings.SECRET_KEY, token_repo)
    validator_policy = DomainRestrictionPolicy(settings.ALLOWED_DOMAIN)
    return AuthService(adapter, user_repo, token_repo, token_mapper, validator_policy)