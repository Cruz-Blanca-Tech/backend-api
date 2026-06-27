# src/contexts/data_quality_triage/infrastructure/mappers/triage_case_mapper.py

from src.contexts.data_quality_triage.domain.shared.entities.triage_case import TriageCase
from src.contexts.data_quality_triage.infrastructure.persistence.model.triage_case_model import TriageCaseModel
from src.contexts.data_quality_triage.domain.shared.value_objects.triage_status import TriageStatus, TriageVerdict
from src.contexts.data_quality_triage.domain.shared.value_objects.field_discrepancy import FieldDiscrepancy

class TriageCaseMapper:

    @staticmethod
    def to_model(case: TriageCase) -> TriageCaseModel:
        return TriageCaseModel(
            id=case.id,
            batch_id=case.batch_id,
            dni_reference=case.dni_reference,
            documents_snapshot=case.documents_snapshot,
            document_ids={k: str(v) for k, v in case.document_ids.items()},
            confidence_scores=case.confidence_scores,
            confidence_threshold=case.confidence_threshold,
            corrected_data=case.corrected_data,
            status=case.status.value,
            verdict=case.verdict.value,
            discrepancies=[d.model_dump() if hasattr(d, "model_dump") else d.__dict__ for d in case.discrepancies],
            rejection_reason=case.rejection_reason,
            resolved_by=case.resolved_by,
            resolved_at=case.resolved_at,
            created_at=case.created_at,
            updated_at=case.updated_at
        )
    
    @staticmethod
    def to_domain(model: TriageCaseModel) -> TriageCase:
        discrepancies = [FieldDiscrepancy(**d) for d in model.discrepancies] if model.discrepancies else []
        import uuid
        
        return TriageCase(
            id=model.id,
            batch_id=model.batch_id,
            dni_reference=model.dni_reference,
            documents_snapshot=model.documents_snapshot,
            document_ids={k: uuid.UUID(v) for k, v in model.document_ids.items()} if model.document_ids else {},
            confidence_scores=model.confidence_scores,
            confidence_threshold=model.confidence_threshold,
            status=TriageStatus(model.status),
            verdict=TriageVerdict(model.verdict),
            discrepancies=discrepancies,
            corrected_data=model.corrected_data,
            rejection_reason=model.rejection_reason,
            resolved_by=model.resolved_by,
            resolved_at=model.resolved_at,
            created_at=model.created_at,
            updated_at=model.updated_at
        )