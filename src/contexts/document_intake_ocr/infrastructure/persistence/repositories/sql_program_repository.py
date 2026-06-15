from __future__ import annotations
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from typing import List, Optional

from src.contexts.document_intake_ocr.domain.repositories.program_repository import ProgramRepository
from src.contexts.document_intake_ocr.domain.entities.program import Program
from src.contexts.document_intake_ocr.infrastructure.persistence.mappers.program_mapper import ProgramMapper
from src.contexts.document_intake_ocr.infrastructure.persistence.model.program_model import ProgramModel

class SqlProgramRepository(ProgramRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, program_id: UUID) -> Optional[Program]:
        # Usamos select() para operaciones asíncronas
        query = select(ProgramModel).filter_by(id=program_id)
        result = await self.session.execute(query)
        db_program = result.scalar_one_or_none()
        
        return ProgramMapper.to_domain(db_program) if db_program else None

    async def list_all(self) -> List[Program]:
        query = select(ProgramModel)
        result = await self.session.execute(query)
        db_programs = result.scalars().all() # .scalars() es vital en async
        
        return [ProgramMapper.to_domain(p) for p in db_programs]

    async def save(self, program: Program) -> None:
        # Usamos el mapper para convertir la entidad al modelo
        db_program = ProgramMapper.to_model(program)
        
        # Merge en async detecta si debe hacer INSERT o UPDATE
        await self.session.merge(db_program)
        
        # El commit DEBE ser await en async
        await self.session.commit()