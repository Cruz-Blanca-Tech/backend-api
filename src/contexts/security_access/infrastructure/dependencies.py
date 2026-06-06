# src/contexts/auth/infrastructure/dependencies.py
from fastapi import Depends
from src.contexts.security_access.application.services.auth_service import AuthService
from src.contexts.security_access.infrastructure.di.auth_container import AuthContainer

from src.core.database import get_async_db


def get_auth_service(db=Depends(get_async_db)) -> AuthService:
    container = AuthContainer(db)
    return container.auth_service