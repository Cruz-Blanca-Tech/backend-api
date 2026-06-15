from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from src.contexts.security_access.application.services.user_service import UserService
from src.core.config import settings 

# Imports de Auth
from src.contexts.security_access.application.policies.auth_policies import DomainRestrictionPolicy
from src.contexts.security_access.application.services.auth_service import AuthService
from src.contexts.security_access.infrastructure.persistence.repositories.sql_alchemy_user_repository import SqlAlchemyUserRepository
from src.contexts.security_access.infrastructure.persistence.repositories.sql_alchemy_token_refresh import SqlRefreshTokenRepository
from src.contexts.security_access.infrastructure.adapters.google_auth_adapter import GoogleIdentityAdapter
from src.contexts.security_access.infrastructure.security.jwt_token_provider import JwtTokenProvider

# NUEVO: Import del UserService

class SecurityAccessContainer:
    def __init__(self, db: Optional[AsyncSession] = None):
        # 1. Componentes que NO necesitan BD (Funcionan en main.py / Middleware)
        self.token_provider = JwtTokenProvider(settings.SECRET_KEY, refresh_token_repo=None)
        self.policy = DomainRestrictionPolicy(settings.ALLOWED_DOMAIN)
        
        # 2. Componentes que SÍ necesitan BD (Se crean solo si recibimos una DB)
        self.auth_service = None
        self.user_service = None # <--- Inicializamos en None por seguridad
        
        if db:
            # Instanciamos los repositorios (Solo 1 vez en memoria)
            self.user_repo = SqlAlchemyUserRepository(db)
            self.token_repo = SqlRefreshTokenRepository(db)
            
            # Re-instanciamos el provider con el repo real
            self.token_provider = JwtTokenProvider(settings.SECRET_KEY, self.token_repo)
            
            # Instanciamos AuthService
            self.auth_service = AuthService(
                GoogleIdentityAdapter(settings.GOOGLE_CLIENT_ID),
                self.user_repo,
                self.token_repo,
                self.token_provider,
                self.policy
            )
            
            # NUEVO: Instanciamos UserService pasándole el MISMO repositorio
            self.user_service = UserService(user_repository=self.user_repo)