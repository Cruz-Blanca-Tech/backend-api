from uuid import UUID
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.contexts.data_quality_triage.domain.entities.triage_case import TriageCase
from src.contexts.data_quality_triage.infrastructure.persistence.mappers.triage_case_mapper import TriageCaseMapper
from src.contexts.data_quality_triage.infrastructure.persistence.model.triage_case_model import TriageCaseModel

class SqlTriageCaseRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def save(self, case: TriageCase) -> None:
        """Persiste o actualiza un caso de triaje."""
        model = TriageCaseMapper.to_model(case)
        self.db.add(model)
        await self.db.commit()

    async def get_by_id(self, case_id: UUID) -> Optional[TriageCase]:
        """Recupera un caso por ID y lo traduce a Dominio."""
        query = select(TriageCaseModel).where(TriageCaseModel.id == case_id)
        result = await self.db.execute(query)
        model = result.scalars().first()
        
        return TriageCaseMapper.to_domain(model) if model else None

    async def get_by_dni_reference(self, dni_reference: str) -> List[TriageCase]:
        """Lista casos pendientes por DNI (útil para el re-procesamiento)."""
        query = select(TriageCaseModel).where(
            TriageCaseModel.dni_reference == dni_reference,
            TriageCaseModel.status == 'PENDING'
        )
        result = await self.db.execute(query)
        return [TriageCaseMapper.to_domain(m) for m in result.scalars().all()]