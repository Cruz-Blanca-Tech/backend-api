# src/contexts/auth/infrastructure/dependencies.py
from fastapi import Depends, HTTPException, Request
from src.contexts.security_access.application.services.auth_service import AuthService
from src.contexts.security_access.application.services.user_service import UserService

from src.contexts.security_access.domain.value_objects.token_claims import TokenClaims
from src.contexts.security_access.infrastructure.di.security_container import SecurityAccessContainer
from src.core.database import get_async_db
from src.core.validators.exceptions import UnauthorizedException


def get_auth_service(db=Depends(get_async_db)) -> AuthService:
    container = SecurityAccessContainer(db)
    return container.auth_service


def get_user_service(db=Depends(get_async_db)) -> UserService:
    container = SecurityAccessContainer(db)
    return container.user_service


def get_current_user(request: Request) -> TokenClaims:
    """
    Dependencia reutilizable que extrae el usuario ya validado 
    por el Middleware desde el estado de la petición.
    """
    user = getattr(request.state, "user", None)
    if not user:
        raise UnauthorizedException("Usuario no autenticado o sesión expirada")
    return user