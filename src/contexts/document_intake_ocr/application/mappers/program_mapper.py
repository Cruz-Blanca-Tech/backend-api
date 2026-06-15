import uuid
from src.contexts.document_intake_ocr.domain.entities.program import Program
from src.contexts.document_intake_ocr.application.schemas.program_schema import ProgramCreateRequest, ProgramResponse, ProgramUpdateRequest

class ProgramMapper:
    """
    Mapper encargado de traducir entre los esquemas de la API y el dominio.
    Mantiene el dominio puro y desacoplado.
    """
    @staticmethod
    def to_domain(request: ProgramCreateRequest) -> Program:
        """Transforma un CreateRequest en una Entidad de Dominio."""
        return Program(
            id=uuid.uuid4(),
            name=request.name,
            description=request.description,
            is_active=request.is_active
        )

    @staticmethod
    def to_response(program: Program) -> ProgramResponse:
        """Transforma una Entidad de Dominio en un ResponseSchema."""
        return ProgramResponse(
            id=program.id,
            name=program.name,
            description=program.description,
            is_active=program.is_active
        )

    @staticmethod
    def update_from_request(program: Program, request: ProgramUpdateRequest) -> Program:
        """
        Actualiza la entidad con los datos del request usando 'exclude_unset'.
        Esta técnica escala infinitamente sin necesidad de sentencias if.
        """
        # exclude_unset=True hace que solo obtengamos los campos que el usuario envió
        update_data = request.model_dump(exclude_unset=True)
        
        # Iteramos dinámicamente sobre los campos presentes
        for key, value in update_data.items():
            if hasattr(program, key):
                setattr(program, key, value)
        
        return program