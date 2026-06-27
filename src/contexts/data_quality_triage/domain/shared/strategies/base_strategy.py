from abc import ABC, abstractmethod
from typing import Dict, Any, List
from src.contexts.data_quality_triage.domain.shared.value_objects.quality_rule_result import QualityRuleResult

class DossierValidationStrategy(ABC):
    @abstractmethod
    def validate(
        self,
        dossier_documents: Dict[str, Dict[str, Any]],
        confidence_scores: Dict[str, float],
        confidence_threshold: float,
    ) -> QualityRuleResult:
        pass

    @abstractmethod
    def get_field_definitions(self) -> List[dict]:
        pass
