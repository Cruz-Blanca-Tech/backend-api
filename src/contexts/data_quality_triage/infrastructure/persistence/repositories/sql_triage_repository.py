import logging
from typing import Optional, List, Tuple
from uuid import UUID
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.contexts.data_quality_triage.domain.shared.entities.triage_case import TriageCase
from src.contexts.data_quality_triage.domain.shared.repositories.triage_repository import TriageRepository
from src.contexts.data_quality_triage.domain.shared.value_objects.triage_status import TriageStatus
from src.contexts.data_quality_triage.infrastructure.persistence.mappers.triage_case_mapper import TriageCaseMapper
from src.contexts.data_quality_triage.infrastructure.persistence.model.triage_case_model import TriageCaseModel

class SqlTriageRepository(TriageRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def save(self, case: TriageCase) -> None:
        db_model = TriageCaseMapper.to_model(case)
        await self.session.merge(db_model)
        await self.session.flush()

    async def get_by_id(self, case_id: UUID) -> Optional[TriageCase]:
        stmt = select(TriageCaseModel).options(selectinload(TriageCaseModel.audit_logs)).where(TriageCaseModel.id == case_id)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return TriageCaseMapper.to_domain(model) if model else None

    async def get_by_dossier(self, batch_id: UUID, dni_reference: str) -> Optional[TriageCase]:
        stmt = select(TriageCaseModel).where(and_(TriageCaseModel.batch_id == batch_id, TriageCaseModel.dni_reference == dni_reference))
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return TriageCaseMapper.to_domain(model) if model else None

    async def list_pending(self, skip: int = 0, limit: int = 20) -> Tuple[List[TriageCase], int]:
        count_stmt = select(func.count()).select_from(TriageCaseModel).where(
            TriageCaseModel.status.in_([TriageStatus.PENDING_REVIEW.value, TriageStatus.IN_REVIEW.value, TriageStatus.CORRECTED.value])
        )
        total = (await self.session.execute(count_stmt)).scalar_one()

        stmt = select(TriageCaseModel).where(
            TriageCaseModel.status.in_([TriageStatus.PENDING_REVIEW.value, TriageStatus.IN_REVIEW.value, TriageStatus.CORRECTED.value])
        ).order_by(TriageCaseModel.created_at.desc()).offset(skip).limit(limit)
        models = (await self.session.execute(stmt)).scalars().all()
        return [TriageCaseMapper.to_domain(m) for m in models], total

    async def list_by_batch_id(self, batch_id: UUID, skip: int = 0, limit: int = 20) -> Tuple[List[TriageCase], int]:
        count_stmt = select(func.count()).select_from(TriageCaseModel).where(TriageCaseModel.batch_id == batch_id)
        total = (await self.session.execute(count_stmt)).scalar_one()

        stmt = select(TriageCaseModel).where(TriageCaseModel.batch_id == batch_id).order_by(TriageCaseModel.created_at.desc()).offset(skip).limit(limit)
        models = (await self.session.execute(stmt)).scalars().all()
        return [TriageCaseMapper.to_domain(m) for m in models], total

    async def get_all_by_batch_id(self, batch_id: UUID) -> List[TriageCase]:
        stmt = select(TriageCaseModel).where(TriageCaseModel.batch_id == batch_id)
        models = (await self.session.execute(stmt)).scalars().all()
        return [TriageCaseMapper.to_domain(m) for m in models]

    async def bulk_save(self, cases: List[TriageCase]) -> None:
        for case in cases:
            db_model = TriageCaseMapper.to_model(case)
            await self.session.merge(db_model)
        await self.session.flush()
