from typing import Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from src.contexts.core_beneficiary_management.infrastructure.persistence.model.beneficiary_models import BeneficiaryModel

class SqlBeneficiaryRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_dni(self, dni: str) -> Optional[BeneficiaryModel]:
        stmt = (
            select(BeneficiaryModel)
            .where(BeneficiaryModel.dni == dni)
            .options(
                selectinload(BeneficiaryModel.medical_record),
                selectinload(BeneficiaryModel.education_record),
                selectinload(BeneficiaryModel.relatives),
                selectinload(BeneficiaryModel.historical_documents)
            )
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def save(self, beneficiary: BeneficiaryModel) -> None:
        self.session.add(beneficiary)
        await self.session.commit()
        await self.session.refresh(beneficiary)
