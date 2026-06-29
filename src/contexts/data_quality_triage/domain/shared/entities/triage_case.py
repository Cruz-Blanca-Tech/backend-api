from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from uuid import UUID, uuid4

from src.contexts.data_quality_triage.domain.shared.value_objects.field_discrepancy import FieldDiscrepancy
from src.contexts.data_quality_triage.domain.shared.value_objects.quality_rule_result import QualityRuleResult
from src.contexts.data_quality_triage.domain.shared.value_objects.triage_status import TriageStatus, TriageVerdict
from src.contexts.data_quality_triage.domain.shared.events.triage_events import DossierRejectedEvent

class TriageCase:
    def __init__(
        self,
        id: UUID,
        batch_id: UUID,
        activity_type: str,
        dni_reference: str,
        dossier_data: Dict[str, Any],
        document_ids: Dict[str, UUID],
        confidence_scores: Dict[str, float],
        status: TriageStatus,
        verdict: TriageVerdict,
        discrepancies: List[FieldDiscrepancy],
        rejection_reason: Optional[str] = None,
        resolved_by: Optional[UUID] = None,
        resolved_at: Optional[datetime] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ):
        self.id = id
        self.batch_id = batch_id
        self.activity_type = activity_type
        self.dni_reference = dni_reference
        self.dossier_data = dossier_data
        self.document_ids = document_ids
        self.confidence_scores = confidence_scores
        self.status = status
        self.verdict = verdict
        self.discrepancies = list(discrepancies)
        self.rejection_reason = rejection_reason
        self.resolved_by = resolved_by
        self.resolved_at = resolved_at
        self.created_at = created_at or datetime.now(timezone.utc)
        self.updated_at = updated_at or datetime.now(timezone.utc)
        self._pending_events: List[Any] = []

    @classmethod
    def create_from_quality_result(
        cls,
        batch_id: UUID,
        activity_type: str,
        dni_reference: str,
        documents: List[Any],
        quality_result: QualityRuleResult,
        dossier_data: Dict[str, Any],
    ) -> "TriageCase":
        document_ids = {}
        confidence_scores = {}
        for doc in documents:
            document_ids[doc.document_code] = doc.id
            confidence_scores[doc.document_code] = doc.confidence_score or 0.0

        if quality_result.is_valid:
            status = TriageStatus.APPROVED
            verdict = TriageVerdict.AUTO_APPROVED
        else:
            status = TriageStatus.PENDING_REVIEW
            verdict = TriageVerdict.REQUIRES_TRIAGE

        case = cls(
            id=uuid4(),
            batch_id=batch_id,
            activity_type=activity_type,
            dni_reference=dni_reference,
            dossier_data=dossier_data,
            document_ids=document_ids,
            confidence_scores=confidence_scores,
            status=status,
            verdict=verdict,
            discrepancies=quality_result.discrepancies,
        )

        return case

    def assign_to_reviewer(self, reviewer_id: UUID) -> None:
        self.status = TriageStatus.IN_REVIEW
        self.resolved_by = reviewer_id
        self.updated_at = datetime.now(timezone.utc)

    def submit_correction(self, corrected_data: Dict[str, Any], corrected_by: UUID) -> None:
        self.dossier_data = corrected_data
        self.status = TriageStatus.CORRECTED
        self.resolved_by = corrected_by
        self.updated_at = datetime.now(timezone.utc)

    def update_discrepancies(self, discrepancies: List[FieldDiscrepancy]) -> None:
        self.discrepancies = list(discrepancies)
        self.updated_at = datetime.now(timezone.utc)

    def approve(self, approved_by: UUID) -> None:
        self.status = TriageStatus.APPROVED
        self.verdict = TriageVerdict.MANUALLY_APPROVED
        self.resolved_by = approved_by
        self.resolved_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)

    def reject(self, rejected_by: UUID, reason: str) -> None:
        self.status = TriageStatus.REJECTED
        self.verdict = TriageVerdict.MANUALLY_REJECTED
        self.rejection_reason = reason
        self.resolved_by = rejected_by
        self.resolved_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)
        self._pending_events.append(
            DossierRejectedEvent(
                triage_case_id=self.id,
                batch_id=self.batch_id,
                dni_reference=self.dni_reference,
                document_ids=list(self.document_ids.values()),
                rejected_by=rejected_by,
                reason=reason,
            )
        )

    @property
    def is_finalized(self) -> bool:
        return self.status in (TriageStatus.APPROVED, TriageStatus.REJECTED)

    @property
    def pending_events(self) -> List[Any]:
        return list(self._pending_events)

    def clear_events(self) -> None:
        self._pending_events.clear()

    @property 
    def min_confidence_score(self) -> float:
        scores = [s for s in self.confidence_scores.values() if s is not None]
        return min(scores) if scores else 0.0
