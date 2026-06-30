from uuid import UUID
from typing import Optional
from src.contexts.core_beneficiary_management.infrastructure.persistence.repositories.sql_beneficiary_repository import SqlBeneficiaryRepository
from src.contexts.core_beneficiary_management.presentation.schemas.beneficiary_schemas import BeneficiaryResponse
from src.contexts.core_beneficiary_management.presentation.mappers.beneficiary_dto_mapper import BeneficiaryDtoMapper

class GetBeneficiaryByIdUseCase:
    def __init__(self, repo: SqlBeneficiaryRepository):
        self.repo = repo

    async def execute(self, id: UUID) -> Optional[BeneficiaryResponse]:
        beneficiary = await self.repo.get_by_id(id)
        if not beneficiary:
            return None
        return BeneficiaryDtoMapper.to_response(beneficiary)
