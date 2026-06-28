from typing import List
from src.contexts.data_quality_triage.domain.shared.dtos.document_dto import DocumentDTO
from src.contexts.data_quality_triage.domain.shared.strategies.base_strategy import TriageStrategy
from src.contexts.data_quality_triage.domain.shared.value_objects.field_discrepancy import FieldDiscrepancy
from src.contexts.data_quality_triage.domain.shared.value_objects.quality_rule_result import QualityRuleResult
from src.contexts.data_quality_triage.domain.shared.entities.triage_case import TriageCase
from uuid import UUID

class GenericTriageStrategy(TriageStrategy):
    def execute(
        self,
        batch_id: UUID,
        activity_type: str,
        dni_reference: str,
        documents: List[DocumentDTO]
    ) -> TriageCase:
        result = QualityRuleResult(
            is_valid=True,
            discrepancies=[],
            confidence_passed=True,
        )
        return TriageCase.create_from_quality_result(
            batch_id=batch_id,
            activity_type=activity_type,
            dni_reference=dni_reference,
            documents=documents,
            quality_result=result,
        )
