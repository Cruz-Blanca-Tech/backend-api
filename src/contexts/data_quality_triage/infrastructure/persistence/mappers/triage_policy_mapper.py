# src/contexts/data_quality_triage/application/mappers/triage_policy_mapper.py
from uuid import UUID, uuid4
from src.contexts.data_quality_triage.domain.shared.entities.triage_policy import TriagePolicy
from src.contexts.data_quality_triage.infrastructure.persistence.model.triage_policy_model import TriagePolicyModel

class TriagePolicyMapper:
    @staticmethod
    def to_domain(model: TriagePolicyModel) -> TriagePolicy:
        """Convierte el modelo de base de datos a una entidad de dominio pura."""
        return TriagePolicy(
            activity_id= model.activity_id,
            required_document_codes=model.required_document_codes
        )

    @staticmethod
    def to_model(entity: TriagePolicy) -> TriagePolicyModel:
        """Convierte la entidad de dominio a un modelo de base de datos para persistencia."""
        return TriagePolicyModel(
            activity_id=str(entity.activity_id),
            required_document_codes=entity.required_document_codes
        )