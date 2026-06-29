from uuid import UUID
from typing import Optional
from src.contexts.document_intake_ocr.domain.repositories.program_repository import ProgramRepository
from src.contexts.document_intake_ocr.application.mappers.program_mapper import ProgramMapper
from src.contexts.document_intake_ocr.application.schemas.program_schema import ProgramResponse

class GetProgramByIdUseCase:
    def __init__(self, repository: ProgramRepository):
        self.repository = repository

    async def execute(self, program_id: UUID) -> Optional[ProgramResponse]:
        program = await self.repository.get_by_id(program_id)
        if not program:
            return None
        return ProgramMapper.to_response(program)
