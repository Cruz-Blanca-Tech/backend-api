from typing import Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from src.contexts.core_beneficiary_management.domain.entities.beneficiary import Beneficiary
from src.contexts.core_beneficiary_management.infrastructure.persistence.model.beneficiary_model import BeneficiaryModel
from src.contexts.core_beneficiary_management.infrastructure.persistence.mappers.beneficiary.beneficiary_mapper import BeneficiaryMapper

class SqlBeneficiaryRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_dni(self, dni: str) -> Optional[Beneficiary]:
        stmt = (
            select(BeneficiaryModel)
            .where(BeneficiaryModel.dni == dni)
            .options(
                selectinload(BeneficiaryModel.medical_record),
                selectinload(BeneficiaryModel.education_record),
                selectinload(BeneficiaryModel.relatives),
                selectinload(BeneficiaryModel.historical_documents),
                selectinload(BeneficiaryModel.enrollments)
            )
        )
        result = await self.session.execute(stmt)
        model = result.scalars().first()
        return BeneficiaryMapper.to_domain(model) if model else None

    async def get_by_id(self, id: UUID) -> Optional[Beneficiary]:
        stmt = (
            select(BeneficiaryModel)
            .where(BeneficiaryModel.id == id)
            .options(
                selectinload(BeneficiaryModel.medical_record),
                selectinload(BeneficiaryModel.education_record),
                selectinload(BeneficiaryModel.relatives),
                selectinload(BeneficiaryModel.historical_documents),
                selectinload(BeneficiaryModel.enrollments)
            )
        )
        result = await self.session.execute(stmt)
        model = result.scalars().first()
        return BeneficiaryMapper.to_domain(model) if model else None

    async def get_all(self, skip: int = 0, limit: int = 100) -> list[Beneficiary]:
        stmt = (
            select(BeneficiaryModel)
            .options(
                selectinload(BeneficiaryModel.medical_record),
                selectinload(BeneficiaryModel.education_record),
                selectinload(BeneficiaryModel.relatives),
                selectinload(BeneficiaryModel.historical_documents),
                selectinload(BeneficiaryModel.enrollments)
            )
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        models = result.scalars().all()
        return [BeneficiaryMapper.to_domain(m) for m in models if m is not None]
        
    async def count(self) -> int:
        from sqlalchemy import func
        stmt = select(func.count()).select_from(BeneficiaryModel)
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def save(self, beneficiary: Beneficiary) -> None:
        model = BeneficiaryMapper.to_persistence(beneficiary)
        # Merge is usually safer when we have complex detached graphs, or add if it's new
        # But if we just extracted from mapper, it is detached. Let's merge.
        merged_model = await self.session.merge(model)
        await self.session.commit()
        # Optional: update entity back? If we need generated IDs, but we use UUIDs.

