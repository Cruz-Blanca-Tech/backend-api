from typing import List
from src.contexts.core_beneficiary_management.infrastructure.persistence.repositories.sql_beneficiary_repository import SqlBeneficiaryRepository
from src.contexts.core_beneficiary_management.presentation.schemas.beneficiary_schemas import PaginatedBeneficiaryResponse
from src.contexts.core_beneficiary_management.presentation.mappers.beneficiary_dto_mapper import BeneficiaryDtoMapper

class GetBeneficiariesUseCase:
    def __init__(self, repo: SqlBeneficiaryRepository):
        self.repo = repo

    async def execute(self, skip: int = 0, limit: int = 100) -> PaginatedBeneficiaryResponse:
        total = await self.repo.count()
        beneficiaries = await self.repo.get_all(skip=skip, limit=limit)
        
        items = [BeneficiaryDtoMapper.to_response(b) for b in beneficiaries]
        
        return PaginatedBeneficiaryResponse(
            items=items,
            total=total,
            skip=skip,
            limit=limit
        )
