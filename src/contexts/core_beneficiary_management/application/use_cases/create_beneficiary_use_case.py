import logging
from typing import Optional
from uuid import UUID

from src.contexts.core_beneficiary_management.infrastructure.persistence.repositories.sql_beneficiary_repository import SqlBeneficiaryRepository
from src.contexts.core_beneficiary_management.presentation.schemas.beneficiary_schemas import (
    BeneficiaryCreateRequest, BeneficiaryResponse
)
from src.contexts.core_beneficiary_management.presentation.mappers.beneficiary_dto_mapper import BeneficiaryDtoMapper
from src.core.validators.exceptions import ConflictException, DomainValidationError

logger = logging.getLogger(__name__)

class CreateBeneficiaryUseCase:
    def __init__(self, repo: SqlBeneficiaryRepository):
        self.repo = repo

    async def execute(
        self,
        request: BeneficiaryCreateRequest,
        explicit_id: Optional[UUID] = None
    ) -> BeneficiaryResponse:
        target_id = explicit_id or request.id

        # 1. Validar unicidad del DNI
        existing_by_dni = await self.repo.get_by_dni(request.dni)
        if existing_by_dni:
            raise ConflictException(f"Ya existe un beneficiario registrado con el DNI: {request.dni}")

        # 2. Si se especificó un ID explícito, validar que no colisione
        if target_id:
            existing_by_id = await self.repo.get_by_id(target_id)
            if existing_by_id:
                raise ConflictException(f"Ya existe un beneficiario registrado con el ID: {target_id}")

        # 3. Mapear a entidad de dominio
        try:
            beneficiary = BeneficiaryDtoMapper.from_create_request(request, explicit_id=target_id)
        except ValueError as e:
            raise DomainValidationError(str(e))

        # 4. Guardar en base de datos
        await self.repo.save(beneficiary)
        logger.info(f"Beneficiary created successfully: ID {beneficiary.id}, DNI {beneficiary.dni.value}")

        # 5. Retornar DTO de respuesta
        return BeneficiaryDtoMapper.to_response(beneficiary)
