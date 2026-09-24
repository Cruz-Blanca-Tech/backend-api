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
        
        # Determine active activity IDs
        active_activity_ids = set()
        try:
            from sqlalchemy import text
            from datetime import date
            today = date.today()
            res = await self.repo.session.execute(
                text("SELECT id FROM activities WHERE is_active = true AND (start_date IS NULL OR start_date <= :t) AND (end_date IS NULL OR end_date >= :t)"),
                {"t": today}
            )
            for row in res.fetchall():
                active_activity_ids.add(str(row[0]))
        except Exception as e:
            pass # Fallback to true if we can't fetch

        items = [BeneficiaryDtoMapper.to_summary_response(b, active_activity_ids) for b in beneficiaries]
        
        return PaginatedBeneficiaryResponse(
            items=items,
            total=total,
            skip=skip,
            limit=limit
        )
