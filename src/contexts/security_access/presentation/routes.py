from fastapi import APIRouter, Depends, Request

from src.contexts.security_access.domain.value_objects.role import Role
from src.contexts.security_access.domain.value_objects.token_claims import TokenClaims
from src.contexts.security_access.infrastructure.api.dependencies.role_checker import RoleChecker
from src.contexts.security_access.presentation.api.auth_router import router as auth_router_instance
from src.contexts.security_access.presentation.dto.login_response import UserResponse

router = APIRouter(prefix="/security", tags=["Security & Access"])

router.include_router(auth_router_instance)

@router.get("/health")
async def health_check():
    return {"status": "ok", "context": "Security & Access"}

@router.get(
    "/me", 
    # 1. Aplicamos el guardia de seguridad. Solo ADMIN u OPERATIVO pueden entrar.
    dependencies=[Depends(RoleChecker([Role.ADMIN, Role.OPERATIVO, Role.VISUALIZADOR]))]
)
async def get_me(request: Request):
    # 2. Como el AuthMiddleware ya validó el token, el usuario está en el request.state
    # Sabemos que es de tipo TokenClaims gracias al tipado estricto que definimos
    usuario_actual: TokenClaims = request.state.user
    
    # 3. Devolvemos la data real del token (adiós al mock)
    return UserResponse(
        email= usuario_actual.email.value,
        full_name= usuario_actual.full_name,
        role= usuario_actual.role.value  
    )