from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.database import get_async_db
from src.contexts.core_beneficiary_management.infrastructure.persistence.repositories.sql_beneficiary_repository import SqlBeneficiaryRepository
from src.contexts.core_beneficiary_management.application.use_cases.get_beneficiaries_use_case import GetBeneficiariesUseCase
from src.contexts.core_beneficiary_management.application.use_cases.get_beneficiary_by_id_use_case import GetBeneficiaryByIdUseCase
from src.contexts.core_beneficiary_management.application.use_cases.patch_beneficiary_use_case import PatchBeneficiaryUseCase

def get_beneficiary_repository(session: AsyncSession = Depends(get_async_db)) -> SqlBeneficiaryRepository:
    return SqlBeneficiaryRepository(session)

def get_beneficiaries_use_case(repo: SqlBeneficiaryRepository = Depends(get_beneficiary_repository)) -> GetBeneficiariesUseCase:
    return GetBeneficiariesUseCase(repo)

def get_beneficiary_by_id_use_case(repo: SqlBeneficiaryRepository = Depends(get_beneficiary_repository)) -> GetBeneficiaryByIdUseCase:
    return GetBeneficiaryByIdUseCase(repo)

def get_patch_beneficiary_use_case(repo: SqlBeneficiaryRepository = Depends(get_beneficiary_repository)) -> PatchBeneficiaryUseCase:
    return PatchBeneficiaryUseCase(repo)
