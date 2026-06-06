# src/contexts/security_access/infrastructure/di/container.py
from sqlalchemy.ext.asyncio import AsyncSession
from src.contexts.security_access.application.policies.auth_policies import DomainRestrictionPolicy
from src.contexts.security_access.application.services.auth_service import AuthService
from src.contexts.security_access.infrastructure.persistence.repositories.sql_alchemy_user_repository import SqlAlchemyUserRepository
from src.contexts.security_access.infrastructure.persistence.repositories.sql_alchemy_token_refresh import SqlRefreshTokenRepository
from src.contexts.security_access.infrastructure.adapters.google_auth_adapter import GoogleIdentityAdapter
from src.contexts.security_access.infrastructure.security.jwt_token_provider import JwtTokenProvider

from src.core.config import settings 

# src/contexts/security_access/infrastructure/di/container.py
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
# ... tus otros imports ...

class AuthContainer:
    def __init__(self, db: Optional[AsyncSession] = None):
        # 1. Componentes que NO necesitan BD (Funcionan en main.py / Middleware)
        self.token_provider = JwtTokenProvider(settings.SECRET_KEY, refresh_token_repo=None)
        self.policy = DomainRestrictionPolicy(settings.ALLOWED_DOMAIN)
        
        # 2. Componentes que SÍ necesitan BD (Se crean solo si recibimos una DB)
        self.auth_service = None
        if db:
            self.user_repo = SqlAlchemyUserRepository(db)
            self.token_repo = SqlRefreshTokenRepository(db)
            
            # Re-instanciamos el provider con el repo real
            self.token_provider = JwtTokenProvider(settings.SECRET_KEY, self.token_repo)
            
            self.auth_service = AuthService(
                GoogleIdentityAdapter(settings.GOOGLE_CLIENT_ID),
                self.user_repo,
                self.token_repo,
                self.token_provider,
                self.policy
            )