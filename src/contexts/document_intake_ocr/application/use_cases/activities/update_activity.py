# src/contexts/document_intake_ocr/application/use_cases/activities/update_activity.py

from uuid import UUID
from src.contexts.document_intake_ocr.domain.repositories.activity_repository import ActivityRepository
from src.contexts.document_intake_ocr.domain.services.activity_validator import ActivityValidator
from src.contexts.document_intake_ocr.application.schemas.activity_schema import ActivityUpdateRequest, ActivityResponse
from src.contexts.document_intake_ocr.application.mappers.activity_mapper import ActivityMapper
from src.core.validators.exceptions import EntityNotFoundException

class UpdateActivityUseCase:
    def __init__(self, activity_repo: ActivityRepository, validator: ActivityValidator):
        self.activity_repo = activity_repo
        self.validator = validator

    async def execute(self, activity_id: UUID, request: ActivityUpdateRequest) -> ActivityResponse:
        # 1. Recuperar
        entity = await self.activity_repo.get_by_id(activity_id)
        if not entity:
            raise EntityNotFoundException(f"La actividad {activity_id} no existe.")

        # 2. Resolver dependencias (Solo si se envían requerimientos)
        configs = []
        if request.requirements is not None:
            config_ids = [r.document_type_config_id for r in request.requirements]
            configs = await self.validator.resolve_and_validate(request.program_id or entity.program_id, config_ids)

        # 3. Actualizar (Delegamos el parcheo al mapper)
        ActivityMapper.update_from_request(entity, request, configs)
        
        # 4. Persistir y Retornar
        await self.activity_repo.save(entity)
        return ActivityMapper.to_response(entity)