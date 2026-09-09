import logging
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status

from src.contexts.core_beneficiary_management.presentation.schemas.beneficiary_schemas import (
    BeneficiaryResponse, PaginatedBeneficiaryResponse, BeneficiaryPatchRequest, BeneficiaryCreateRequest
)
from src.contexts.core_beneficiary_management.infrastructure.dependencies.beneficiary_deps import (
    get_beneficiaries_use_case, get_beneficiary_by_id_use_case, get_patch_beneficiary_use_case,
    get_create_beneficiary_use_case
)
from src.contexts.core_beneficiary_management.application.use_cases.get_beneficiaries_use_case import GetBeneficiariesUseCase
from src.contexts.core_beneficiary_management.application.use_cases.get_beneficiary_by_id_use_case import GetBeneficiaryByIdUseCase
from src.contexts.core_beneficiary_management.application.use_cases.patch_beneficiary_use_case import PatchBeneficiaryUseCase
from src.contexts.core_beneficiary_management.application.use_cases.create_beneficiary_use_case import CreateBeneficiaryUseCase
from src.core.validators.exceptions import ConflictException, DomainValidationError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/beneficiaries", tags=["Master Data - Beneficiaries"])

@router.get("/", response_model=PaginatedBeneficiaryResponse)
async def get_beneficiaries(
    skip: int = 0,
    limit: int = 100,
    use_case: GetBeneficiariesUseCase = Depends(get_beneficiaries_use_case)
):
    """Obtiene una lista paginada de todos los beneficiarios."""
    return await use_case.execute(skip=skip, limit=limit)

@router.get("/{beneficiary_id}", response_model=BeneficiaryResponse)
async def get_beneficiary(
    beneficiary_id: UUID,
    use_case: GetBeneficiaryByIdUseCase = Depends(get_beneficiary_by_id_use_case)
):
    """Obtiene el perfil completo de un beneficiario por su ID."""
    beneficiary = await use_case.execute(beneficiary_id)
    if not beneficiary:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Beneficiary not found")
    return beneficiary

@router.patch("/{beneficiary_id}", response_model=BeneficiaryResponse)
async def patch_beneficiary(
    beneficiary_id: UUID,
    payload: BeneficiaryPatchRequest,
    use_case: PatchBeneficiaryUseCase = Depends(get_patch_beneficiary_use_case)
):
    """Actualiza parcialmente la información de un beneficiario (médica, educativa, familiar)."""
    try:
        return await use_case.execute(beneficiary_id, payload)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Error patching beneficiary {beneficiary_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/", response_model=BeneficiaryResponse, status_code=status.HTTP_201_CREATED)
async def create_beneficiary(
    payload: BeneficiaryCreateRequest,
    use_case: CreateBeneficiaryUseCase = Depends(get_create_beneficiary_use_case)
):
    """Crea manualmente un nuevo beneficiario en el sistema sin pasar por OCR."""
    try:
        return await use_case.execute(payload)
    except ConflictException as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e.message))
    except (DomainValidationError, ValueError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating beneficiary: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.post("/{beneficiary_id}", response_model=BeneficiaryResponse, status_code=status.HTTP_201_CREATED)
async def create_beneficiary_with_id(
    beneficiary_id: UUID,
    payload: BeneficiaryCreateRequest,
    use_case: CreateBeneficiaryUseCase = Depends(get_create_beneficiary_use_case)
):
    """Crea manualmente un nuevo beneficiario especificando su ID en la URL."""
    try:
        return await use_case.execute(payload, explicit_id=beneficiary_id)
    except ConflictException as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e.message))
    except (DomainValidationError, ValueError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating beneficiary with id {beneficiary_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

