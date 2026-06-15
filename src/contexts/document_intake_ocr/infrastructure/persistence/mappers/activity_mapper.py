# src/contexts/document_intake_ocr/infrastructure/persistence/mappers/activity_mapper.py

from src.contexts.document_intake_ocr.domain.entities.activity import Activity
from src.contexts.document_intake_ocr.infrastructure.persistence.mappers.activity_requirement_mapper import ActivityRequirementMapper
from src.contexts.document_intake_ocr.infrastructure.persistence.model.activity_model import ActivityModel

class ActivityMapper:
    @staticmethod
    def to_domain(model: ActivityModel) -> Activity:
        # 1. Transformamos los registros de la tabla intermedia en Value Objects del Dominio

        requirements_domain = [
            ActivityRequirementMapper.to_domain(req)
            for req in model.requirements
        ]

        return Activity(
            id=model.id,
            program_id=model.program_id,
            name=model.name,
            required_documents=requirements_domain,
            is_active=model.is_active
        )

    @staticmethod
    def to_model(entity: Activity) -> ActivityModel:
        # 1. Creamos el modelo cabecera
        model = ActivityModel(
            id=entity.id,
            program_id=entity.program_id,
            name=entity.name,
            is_active=entity.is_active
        )
        
        # 2. Usamos el ActivityRequirementMapper para mapear la colección
        model.requirements = [
            ActivityRequirementMapper.to_model(req, entity.id)
            for req in entity.required_documents
        ]
        
        return model