# src/contexts/security_access/infrastructure/security/jwt_token_provider.py

import hashlib

import jwt
import secrets
from datetime import datetime, timedelta
from typing import Dict, Any

from src.contexts.security_access.domain.ports.token_provider import TokenProvider, TokenPair
from src.contexts.security_access.domain.entities.user import User
from src.contexts.security_access.domain.value_objects.token_claims import TokenClaims
from src.contexts.security_access.domain.repositories.refresh_token_repository import RefreshTokenRepository

class JwtTokenProvider(TokenProvider):
    def __init__(
        self, 
        secret_key: str, 
        refresh_token_repo: RefreshTokenRepository,
        algorithm: str = "HS256", 
        expiration_hours: int = 1 
    ):
        self.secret_key = secret_key
        self.refresh_token_repo = refresh_token_repo
        self.algorithm = algorithm
        self.expiration_hours = expiration_hours

    def hash_token(self, token: str) -> str:
        """
        Convierte el token aleatorio en un hash SHA-256 
        para guardarlo de forma segura en la base de datos.
        """
        return hashlib.sha256(token.encode()).hexdigest()
    
    async def create_internal_token_pair(self, user: User) -> TokenPair:
        # 1. Generar Access Token
        print(user)
        claims = TokenClaims(email=user.email, role=user.role, full_name=user.full_name)
        payload = self._build_payload(claims)
        access_token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        
        # 2. Generar Refresh Token (crudo)
        refresh_token = secrets.token_urlsafe(64)
        refresh_expires_at = datetime.utcnow() + timedelta(days=7)
        
        # 3. Hashear antes de guardar (ahora que el provider conoce cómo hacerlo)
        token_hash = self.hash_token(refresh_token)
        
        # 4. Llamar al repo usando el parámetro correcto: token_hash
        await self.refresh_token_repo.save(
            user_id=user.id, 
            token_hash=token_hash,  # <--- AQUÍ ESTABA EL ERROR
            expires_at=refresh_expires_at
        )
        return TokenPair(access_token=access_token, refresh_token=refresh_token)
    
    def decode_internal_token(self, token: str) -> TokenClaims:
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return TokenClaims.from_dict(payload)
        except jwt.ExpiredSignatureError:
            raise PermissionError("El token ha expirado.")
        except jwt.InvalidTokenError:
            raise PermissionError("Token inválido.")
    
    def _build_payload(self, claims: TokenClaims) -> Dict[str, Any]:
        now = datetime.utcnow()
        payload = claims.to_dict()
        payload.update({
            "exp": now + timedelta(hours=self.expiration_hours),
            "iat": now
        })
        return payload