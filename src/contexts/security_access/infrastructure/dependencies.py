# src/contexts/auth/infrastructure/dependencies.py
from fastapi import Depends
from src.contexts.security_access.application.services.auth_service import AuthService
from src.contexts.security_access.application.services.user_service import UserService

from src.contexts.security_access.infrastructure.di.security_container import SecurityAccessContainer
from src.core.database import get_async_db


def get_auth_service(db=Depends(get_async_db)) -> AuthService:
    container = SecurityAccessContainer(db)
    return container.auth_service


def get_user_service(db=Depends(get_async_db)) -> UserService:
    container = SecurityAccessContainer(db)
    return container.user_service