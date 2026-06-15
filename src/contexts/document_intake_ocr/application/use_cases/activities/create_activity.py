# src/contexts/document_intake_ocr/application/use_cases/activities/create_activity.py

from src.contexts.document_intake_ocr.application.schemas.activity_schema import ActivityCreateRequest, ActivityResponse
from src.contexts.document_intake_ocr.application.mappers.activity_mapper import ActivityMapper
from src.contexts.document_intake_ocr.domain.repositories.activity_repository import ActivityRepository
from src.contexts.document_intake_ocr.domain.services.activity_validator import ActivityValidator

class CreateActivityUseCase:
    def __init__(self, activity_repo: ActivityRepository, validator: ActivityValidator):
        self.activity_repo = activity_repo
        self.validator = validator

    async def execute(self, request: ActivityCreateRequest) -> ActivityResponse:
        # 1. Resolve and validate dependencies in one step
        config_ids = [r.document_type_config_id for r in request.requirements]
        configs = await self.validator.resolve_and_validate(request.program_id, config_ids)
        
        # 2. Map and persist
        activity = ActivityMapper.to_domain(request, configs)
        await self.activity_repo.save(activity)
        
        # 3. Respond
        return ActivityMapper.to_response(activity)