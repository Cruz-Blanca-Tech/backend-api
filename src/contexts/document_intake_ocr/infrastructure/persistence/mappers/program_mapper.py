

from src.contexts.document_intake_ocr.domain.entities.program import Program
from src.contexts.document_intake_ocr.infrastructure.persistence.model.program_model import ProgramModel

class ProgramMapper:
    @staticmethod
    def to_domain(model: ProgramModel) -> Program:
        return Program(
            id=model.id,
            name=model.name,
            description=model.description,
            is_active=model.is_active
        )

    @staticmethod
    def to_model(entity: Program) -> ProgramModel:
        return ProgramModel(
            id=entity.id,
            name=entity.name,
            description=entity.description,
            is_active=entity.is_active
        )