from uuid import UUID
from src.contexts.core_beneficiary_management.infrastructure.persistence.repositories.sql_beneficiary_repository import SqlBeneficiaryRepository
from src.contexts.core_beneficiary_management.presentation.schemas.beneficiary_schemas import BeneficiaryPatchRequest, BeneficiaryResponse
from src.contexts.core_beneficiary_management.presentation.mappers.beneficiary_dto_mapper import BeneficiaryDtoMapper

class PatchBeneficiaryUseCase:
    def __init__(self, repo: SqlBeneficiaryRepository):
        self.repo = repo

    async def execute(self, id: UUID, patch_request: BeneficiaryPatchRequest) -> BeneficiaryResponse:
        beneficiary = await self.repo.get_by_id(id)
        if not beneficiary:
            raise ValueError(f"Beneficiary with id {id} not found")
            
        updated_beneficiary = BeneficiaryDtoMapper.patch_domain(beneficiary, patch_request)
        
        await self.repo.save(updated_beneficiary)
        
        return BeneficiaryDtoMapper.to_response(updated_beneficiary)
