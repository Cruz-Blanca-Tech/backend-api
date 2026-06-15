from typing import List, Optional
from uuid import UUID
from src.contexts.document_intake_ocr.domain.repositories.activity_repository import ActivityRepository
from src.contexts.document_intake_ocr.application.schemas.activity_schema import ActivityResponse
from src.contexts.document_intake_ocr.application.mappers.activity_mapper import ActivityMapper

class ListActivitiesUseCase:
    def __init__(self, repository: ActivityRepository):
        self.repository = repository

    async def execute(self, program_id: Optional[UUID] = None) -> List[ActivityResponse]:
        # 1. Selección de estrategia (Filtrar por programa o traer todo)
        if program_id:
            entities = await self.repository.get_by_program_id(program_id)
        else:
            # Traemos todas las activas
            entities = await self.repository.list_all_active()
            
        # 2. Mapeo asíncrono-safe
        return [ActivityMapper.to_response(entity) for entity in entities]