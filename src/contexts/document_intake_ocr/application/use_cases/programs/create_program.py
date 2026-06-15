from typing import List
from src.contexts.document_intake_ocr.domain.repositories.program_repository import ProgramRepository
from src.contexts.document_intake_ocr.application.mappers.program_mapper import ProgramMapper
from src.contexts.document_intake_ocr.application.schemas.program_schema import ProgramCreateRequest, ProgramResponse

class CreateProgramUseCase:
    """
    Orquesta el flujo para registrar un nuevo Programa en el sistema.
    Ahora implementado con soporte para persistencia asíncrona.
    """
    def __init__(self, repository: ProgramRepository):
        self.repository = repository

    # Cambiado a async def
    async def execute(self, request: ProgramCreateRequest) -> ProgramResponse:
        # 1. Transformar el contrato de entrada (Request) a Entidad de Dominio
        # (Esto suele ser síncrono porque es solo mapeo de objetos en memoria)
        program_entity = ProgramMapper.to_domain(request)
        
        # 2. Persistir la entidad a través del puerto (Repositorio)
        # DEBE SER await porque el repositorio ahora es asíncrono
        await self.repository.save(program_entity)
        
        # 3. Transformar la Entidad persistida al contrato de salida (Response)
        return ProgramMapper.to_response(program_entity)