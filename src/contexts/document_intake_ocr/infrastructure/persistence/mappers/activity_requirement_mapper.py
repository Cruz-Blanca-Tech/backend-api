# src/contexts/document_intake_ocr/infrastructure/persistence/mappers/activity_requirement_mapper.py

from uuid import UUID
from src.contexts.document_intake_ocr.domain.entities.activity import ActivityRequirement
from src.contexts.document_intake_ocr.infrastructure.persistence.model.activity_requirement_model import ActivityRequirementModel
from src.contexts.document_intake_ocr.infrastructure.persistence.mappers.document_catalog_mapper import DocumentCatalogMapper

class ActivityRequirementMapper:
    @staticmethod
    def to_domain(model: ActivityRequirementModel) -> ActivityRequirement:
        return ActivityRequirement(
            document_config=DocumentCatalogMapper.to_domain(model.document_config),
            is_required=model.is_required,
            confidence_threshold=model.confidence_threshold
        )

    @staticmethod
    def to_model(entity: ActivityRequirement, activity_id: UUID) -> ActivityRequirementModel:
        """
        Traduce el Value Object de dominio a una instancia del Modelo de BD.
        """
        return ActivityRequirementModel(
            activity_id=activity_id, # Inyectamos la relación padre
            document_type_config_id=entity.document_config.id, # Extraemos el ID del objeto configurado
            is_required=entity.is_required,
            confidence_threshold=entity.confidence_threshold
        )