from typing import List
from uuid import UUID
from src.contexts.data_quality_triage.domain.entities.triage_case import TriageCase
from src.contexts.data_quality_triage.domain.value_objects.field_discrepancy import FieldDiscrepancy
from src.contexts.data_quality_triage.domain.value_objects.triage_status import TriageStatus, TriageVerdict
from src.contexts.data_quality_triage.infrastructure.persistence.model.triage_case_model import TriageCaseModel

class TriageCaseMapper:
    @staticmethod
    def to_model(entity: TriageCase) -> TriageCaseModel:
        return TriageCaseModel(
            id=entity.id,
            batch_id=entity.batch_id,
            dni_reference=entity.dni_reference,
            documents_snapshot=entity.documents_snapshot,
            document_ids={code: str(uid) for code, uid in entity.document_ids.items()},
            confidence_scores=entity.confidence_scores,
            confidence_threshold=entity.confidence_threshold,
            corrected_data=entity.corrected_data,
            status=entity.status.value,
            verdict=entity.verdict.value,
            discrepancies=[d.to_dict() for d in entity.discrepancies],
            rejection_reason=entity.rejection_reason,
            resolved_by=entity.resolved_by,
            resolved_at=entity.resolved_at,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )

    @staticmethod
    def to_domain(model: TriageCaseModel) -> TriageCase:
        discrepancies = [FieldDiscrepancy.from_dict(d) for d in (model.discrepancies or [])]
        document_ids = {code: UUID(uid_str) for code, uid_str in (model.document_ids or {}).items()}

        return TriageCase(
            id=model.id,
            batch_id=model.batch_id,
            dni_reference=model.dni_reference,
            documents_snapshot=model.documents_snapshot or {},
            document_ids=document_ids,
            confidence_scores=model.confidence_scores or {},
            confidence_threshold=model.confidence_threshold,
            corrected_data=model.corrected_data,
            status=TriageStatus(model.status),
            verdict=TriageVerdict(model.verdict),
            discrepancies=discrepancies,
            rejection_reason=model.rejection_reason,
            resolved_by=model.resolved_by,
            resolved_at=model.resolved_at,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
