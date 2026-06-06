# src/contexts/security_access/infrastructure/api/dependencies/role_checker.py
from fastapi import HTTPException, Request, status
from src.contexts.security_access.domain.value_objects.role import Role
from src.contexts.security_access.domain.value_objects.token_claims import TokenClaims

class RoleChecker:
    def __init__(self, allowed_roles: list[Role]):
        self.allowed_roles = allowed_roles

    def __call__(self, request: Request):
        # 1. Recuperamos el objeto y le DECIMOS a Python qué tipo es
        user: TokenClaims = getattr(request.state, "user", None)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Usuario no autenticado"
            )

        # 2. Ahora usamos la notación de punto (Seguridad de Tipos)
        # Tu IDE ahora sabrá automáticamente que .role existe
        if user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permisos insuficientes. Se requiere: {', '.join([r.value for r in self.allowed_roles])}"
            )
        
        return True