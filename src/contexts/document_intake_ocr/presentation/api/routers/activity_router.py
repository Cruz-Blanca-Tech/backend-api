from fastapi import APIRouter, Depends, HTTPException, Query, status
from uuid import UUID
from typing import List, Optional

# Importamos estrictamente contratos (Schemas)
from src.contexts.document_intake_ocr.application.schemas.activity_schema import (
    ActivityCreateRequest,
    ActivityUpdateRequest,
    ActivityResponse
)

# Importamos las clases de tipado para los Casos de Uso
from src.contexts.document_intake_ocr.application.use_cases.activities.create_activity import CreateActivityUseCase
from src.contexts.document_intake_ocr.application.use_cases.activities.update_activity import UpdateActivityUseCase
from src.contexts.document_intake_ocr.application.use_cases.activities.list_activities import ListActivitiesUseCase
from src.contexts.document_intake_ocr.application.use_cases.activities.get_activity_by_id import GetActivityByIdUseCase
from src.core.validators.exceptions import EntityNotFoundException

# IMPORTACIÓN DE ARQUITECTURA: Consumimos la fábrica modular de dependencias
from src.contexts.document_intake_ocr.infrastructure.dependencies.activity_deps import (
    get_create_activity_use_case,
    get_update_activity_use_case,
    get_list_activities_use_case,
    get_by_activity_id_use_case
)
from src.contexts.security_access.infrastructure.api.dependencies.policies import ALLOW_ADMIN_ONLY, ALLOW_ANY_STAFF

router = APIRouter(prefix="/activities", tags=["Activities Configuration"])


@router.post("/", response_model=ActivityResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(ALLOW_ADMIN_ONLY)])
async def create_activity(
    request: ActivityCreateRequest,
    use_case: CreateActivityUseCase = Depends(get_create_activity_use_case)
):
    """Crea una campaña o actividad asociándole sus requerimientos documentales."""
    return await use_case.execute(request)


@router.patch("/{activity_id}", response_model=ActivityResponse, dependencies=[Depends(ALLOW_ADMIN_ONLY)])
async def update_activity(
    activity_id: UUID,
    request: ActivityUpdateRequest,
    use_case: UpdateActivityUseCase = Depends(get_update_activity_use_case)
):
    """Actualiza los metadatos de control de la actividad."""
    try:
        return await use_case.execute(activity_id, request)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/", response_model=List[ActivityResponse])
async def list_activities(
    # program_id es opcional. Por defecto es None.
    program_id: Optional[UUID] = Query(None, description="ID del programa para filtrar actividades"),
    use_case: ListActivitiesUseCase = Depends(get_list_activities_use_case)
):
    """
    Lista actividades.
    - Si se envía program_id: filtra por ese programa.
    - Si no se envía: lista todas las actividades activas.
    """
    return await use_case.execute(program_id=program_id)

@router.get("/{activity_id}", response_model=ActivityResponse)
async def get_activity(
    activity_id: UUID,
    use_case: GetActivityByIdUseCase = Depends(get_by_activity_id_use_case)
):
    """Obtiene los detalles de una campaña o actividad específica."""
    try:
        return await use_case.execute(activity_id)
    except EntityNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))