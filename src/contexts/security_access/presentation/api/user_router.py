from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from uuid import UUID

# 1. Importamos nuestros DTOs
from src.contexts.security_access.domain.value_objects.token_claims import TokenClaims
from src.contexts.security_access.infrastructure.api.dependencies.policies import ALLOW_ADMIN_ONLY, ALLOW_ANY_STAFF
from src.contexts.security_access.infrastructure.dependencies import get_current_user, get_user_service
from src.contexts.security_access.presentation.dto.user_dto import UpdateRoleRequest, UserResponse

# 2. Importamos el Application Service y su inyector
from src.contexts.security_access.application.services.user_service import UserService
# Asumimos que agregaste get_user_service a tu archivo central de dependencias

# 3. Importamos las Políticas de Seguridad (RBAC centralizado)

router = APIRouter(prefix="/users")

@router.get("/", response_model=List[UserResponse], dependencies=[Depends(ALLOW_ANY_STAFF)])
async def list_users(
    user_service: UserService = Depends(get_user_service)
):
    """
    Lista todos los usuarios del sistema. 
    Protección: Solo administradores y revisores pueden ver esta lista.
    """
    # El Application Service orquesta la    llamada al repositorio
    users = await user_service.list_users()

    users_list = [UserResponse(id=user.id, email=user.email.value, role=user.role, full_name=user.full_name) for user in users]
   
    return users_list


@router.patch("/{user_id}/role", response_model=UserResponse, dependencies=[Depends(ALLOW_ANY_STAFF)])
async def update_user_role(
    user_id: UUID,
    request: UpdateRoleRequest,
    user_service: UserService = Depends(get_user_service)
):
    """
    Modifica el nivel de acceso (rol) de un usuario existente.
    Protección: Operación CRÍTICA. Exclusiva para el rol ADMIN.
    """
    try:
        # 1. Delegamos la lógica al Application Service
        updated_user = await user_service.update_role(user_id=user_id, new_role=request.role)
        return UserResponse(
            id= updated_user.id,
            email= updated_user.email.value,
            role= updated_user.role,
            full_name= updated_user.full_name
        )

    except ValueError as e:
        # Capturamos el caso donde el usuario no existe en la BD
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=str(e)
        )
    except Exception as e:
        # Capturamos cualquier otro error imprevisto (Base de datos caída, etc.)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ocurrió un error al intentar actualizar el rol del usuario."
        )
    
@router.get("/me")
async def get_me(current_user: TokenClaims = Depends(get_current_user)):
    """
    Devuelve la información del perfil del usuario autenticado.
    """
    return UserResponse(
        id=current_user.user_id,
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role.value
    )