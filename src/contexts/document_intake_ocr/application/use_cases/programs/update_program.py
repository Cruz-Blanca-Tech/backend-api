from uuid import UUID
from src.contexts.document_intake_ocr.domain.repositories.program_repository import ProgramRepository
from src.contexts.document_intake_ocr.application.mappers.program_mapper import ProgramMapper
from src.contexts.document_intake_ocr.application.schemas.program_schema import ProgramResponse, ProgramUpdateRequest

class UpdateProgramUseCase:
    """
    Orquesta el flujo para actualizar (PATCH) parcialmente un Programa existente.
    """
    def __init__(self, repository: ProgramRepository):
        self.repository = repository

    async def  execute(self, program_id: UUID, request: ProgramUpdateRequest) -> ProgramResponse:
        # 1. Recuperar la entidad de dominio existente
        program_entity = self.repository.get_by_id(program_id)
        
        if not program_entity:
            # En FastAPI, luego capturaremos este ValueError para lanzar un HTTP 404
            raise ValueError(f"Programa con ID {program_id} no encontrado en el sistema.")

        # 2. Aplicar los cambios parciales usando nuestro Mapper inteligente
        # ¡Cero 'ifs' aquí! Toda la magia de exclude_unset está en el Mapper.
        updated_entity = ProgramMapper.update_from_request(program_entity, request)
        
        # 3. Persistir los cambios
        await self.repository.save(updated_entity)
        
        # 4. Retornar el contrato de salida actualizado
        return ProgramMapper.to_response(updated_entity)