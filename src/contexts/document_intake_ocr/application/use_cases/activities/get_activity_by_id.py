# src/contexts/document_intake_ocr/application/use_cases/activities/get_activity_by_id.py

from uuid import UUID
from typing import Optional
from src.contexts.document_intake_ocr.domain.repositories.activity_repository import ActivityRepository
from src.contexts.document_intake_ocr.application.mappers.activity_mapper import ActivityMapper
from src.contexts.document_intake_ocr.application.schemas.activity_schema import ActivityResponse
from src.core.validators.exceptions import EntityNotFoundException

class GetActivityByIdUseCase:
    def __init__(self, repository: ActivityRepository):
        self.repository = repository

    async def execute(self, activity_id: UUID) -> ActivityResponse:
        # 1. Recuperar del repositorio
        activity = await self.repository.get_by_id(activity_id)
        
        # 2. Manejo de error de negocio (Domain Exception)
        if not activity:
            raise EntityNotFoundException(f"Actividad con ID {activity_id} no encontrada.")
            
        # 3. Mapear a DTO de respuesta
        return ActivityMapper.to_response(activity)