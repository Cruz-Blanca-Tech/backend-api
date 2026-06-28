from abc import ABC, abstractmethod
from typing import Dict, Any
from src.contexts.data_quality_triage.domain.shared.value_objects.quality_rule_result import QualityRuleResult
from src.contexts.data_quality_triage.domain.shared.dtos.document_dto import DocumentDTO
from src.contexts.data_quality_triage.domain.shared.entities.triage_case import TriageCase
from typing import List
from uuid import UUID

class TriageStrategy(ABC):
    @abstractmethod
    def execute(
        self,
        batch_id: UUID,
        activity_type: str,
        dni_reference: str,
        documents: List[DocumentDTO]
    ) -> TriageCase:
        pass
