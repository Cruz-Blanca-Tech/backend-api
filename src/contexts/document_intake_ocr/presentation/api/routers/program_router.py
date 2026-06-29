from fastapi import APIRouter, Depends, HTTPException, status
from uuid import UUID
from typing import List

# Importamos las clases de tipado para los Casos de Uso
from src.contexts.document_intake_ocr.application.use_cases.programs.create_program import CreateProgramUseCase
from src.contexts.document_intake_ocr.application.use_cases.programs.list_program import ListProgramsUseCase
from src.contexts.document_intake_ocr.application.use_cases.programs.update_program import UpdateProgramUseCase
from src.contexts.document_intake_ocr.application.use_cases.programs.get_program import GetProgramByIdUseCase

# Importamos estrictamente contratos (Schemas)
from src.contexts.document_intake_ocr.application.schemas.program_schema import (
    ProgramCreateRequest, 
    ProgramUpdateRequest, 
    ProgramResponse
)
# IMPORTACIÓN DE ARQUITECTURA: Consumimos la fábrica modular de dependencias
from src.contexts.document_intake_ocr.infrastructure.dependencies.program_deps import (
    get_create_program_use_case,
    get_list_programs_use_case,
    get_update_program_use_case,
    get_program_by_id_use_case
)
from src.contexts.security_access.infrastructure.api.dependencies.policies import ALLOW_ADMIN_OR_REVIEWER, ALLOW_ANY_STAFF

router = APIRouter(prefix="/programs", tags=["Programs Master Data"])


@router.post("/", response_model=ProgramResponse, dependencies=[Depends(ALLOW_ADMIN_OR_REVIEWER)])
async def create_program(
    request: ProgramCreateRequest,
    use_case: CreateProgramUseCase = Depends(get_create_program_use_case)
):
    """Registra un nuevo programa institucional de la ONG."""
    return await use_case.execute(request)


@router.patch("/{program_id}", response_model=ProgramResponse, dependencies=[Depends(ALLOW_ADMIN_OR_REVIEWER)])
async def update_program(
    program_id: UUID,
    request: ProgramUpdateRequest,
    use_case: UpdateProgramUseCase = Depends(get_update_program_use_case)
):
    """Actualiza parcialmente los datos de un programa por su UUID."""
    try:
        return await use_case.execute(program_id, request)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/", response_model=List[ProgramResponse],dependencies=[Depends(ALLOW_ANY_STAFF)])
async def list_programs(use_case: ListProgramsUseCase = Depends(get_list_programs_use_case)):
    """Lista todos los programas institucionales vigentes."""
    return await use_case.execute()

@router.get("/{program_id}", response_model=ProgramResponse, dependencies=[Depends(ALLOW_ANY_STAFF)])
async def get_program(
    program_id: UUID,
    use_case: GetProgramByIdUseCase = Depends(get_program_by_id_use_case)
):
    """Obtiene un programa institucional por su ID."""
    program = await use_case.execute(program_id)
    if not program:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Program not found")
    return program