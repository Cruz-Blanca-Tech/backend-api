# src/contexts/document_intake_ocr/application/use_cases/programs/list_programs.py

from typing import List
from src.contexts.document_intake_ocr.domain.repositories.program_repository import ProgramRepository
from src.contexts.document_intake_ocr.application.mappers.program_mapper import ProgramMapper
from src.contexts.document_intake_ocr.application.schemas.program_schema import ProgramResponse

class ListProgramsUseCase:
    """
    Orquesta el flujo para recuperar y listar todos los programas activos en el sistema.
    Indispensable para alimentar los selectores y tablas en la interfaz del usuario.
    """
    def __init__(self, repository: ProgramRepository):
        self.repository = repository

    async def execute(self) -> List[ProgramResponse]:
        # DEBE TENER await
        programs = await self.repository.list_all()
        return [ProgramMapper.to_response(program) for program in programs]