# src/contexts/security_access/application/services/auth_service.py

from datetime import datetime, timedelta
from typing import Optional
from src.contexts.security_access.domain.ports.identity_provider_port import IdentityProviderPort
from src.contexts.security_access.domain.ports.token_provider_port import TokenProviderPort, TokenPair
from src.contexts.security_access.domain.entities.user import User
from src.contexts.security_access.domain.repositories.user_repository import UserRepository
from src.contexts.security_access.domain.repositories.refresh_token_repository import RefreshTokenRepository
from src.contexts.security_access.application.policies.auth_policies import DomainRestrictionPolicy

class AuthService:
    def __init__(
        self, 
        external_auth_provider: IdentityProviderPort, 
        user_repo: UserRepository, 
        refresh_token_repo: RefreshTokenRepository,
        token_provider: TokenProviderPort,
        policy: DomainRestrictionPolicy
    ):
        self.external_auth_provider = external_auth_provider
        self.user_repo = user_repo
        self.refresh_token_repo = refresh_token_repo
        self.token_provider = token_provider
        self.policy = policy

    async def authenticate_user(self, google_token: str) -> TokenPair:
        """Orquesta el inicio de sesión y aprovisionamiento de usuario."""
        
        external_identity = self.external_auth_provider.verify_token(google_token)
        self.policy.check(external_identity.email)
        
        user: Optional[User] = await self.user_repo.get_by_email(str(external_identity.email))
        
        if not user:
            user = User.create_new_user(external_identity)
            await self.user_repo.save(user)
        else:
            user.update_profile(external_identity)
            await self.user_repo.save(user)
            
        token_pair: TokenPair = await self.token_provider.create_internal_token_pair(user)
        
        # Hasheo de seguridad antes de persistir
        token_hash = self.token_provider.hash_token(token_pair.refresh_token)
        absolute_expiration = datetime.utcnow() + timedelta(days=14)
        
        await self.refresh_token_repo.save(
            user_id=user.id, 
            token_hash=token_hash, 
            expires_at=absolute_expiration
        )
        
        return token_pair

    async def refresh_user_session(self, old_refresh_token: str) -> TokenPair:
        """Gestiona la rotación de tokens y expiración absoluta."""
        
        # Validamos contra hash
        token_hash = self.token_provider.hash_token(old_refresh_token)
        active_session = await self.refresh_token_repo.get_session_by_token(token_hash)
        
        if not active_session:
            raise PermissionError("Sesión inválida o expirada.")
            
        user: Optional[User] = await self.user_repo.get_by_email(active_session.user_id)
        if not user:
            raise PermissionError("Usuario no encontrado.")

        # Rotación: Quemar el token viejo
        await self.refresh_token_repo.delete(token_hash)

        # Generar nuevo par
        new_token_pair: TokenPair = await self.token_provider.create_internal_token_pair(user)

        # Hashear y guardar nuevo token
        new_token_hash = self.token_provider.hash_token(new_token_pair.refresh_token)
        await self.refresh_token_repo.save(
            user_id=user.id,
            token_hash=new_token_hash,
            expires_at=active_session.expires_at # Mantenemos la expiración original (14 días desde el inicio)
        )

        return new_token_pair
    
    async def logout_user(self, refresh_token: str) -> None:
        """Invalida la sesión actual del usuario."""
        token_hash = self.token_provider.hash_token(refresh_token)
        await self.refresh_token_repo.delete(token_hash)