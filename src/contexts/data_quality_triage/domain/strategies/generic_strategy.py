from typing import Dict, Any, List
from src.contexts.data_quality_triage.domain.strategies.base_strategy import DossierValidationStrategy
from src.contexts.data_quality_triage.domain.value_objects.field_discrepancy import FieldDiscrepancy
from src.contexts.data_quality_triage.domain.value_objects.quality_rule_result import QualityRuleResult

class GenericStrategy(DossierValidationStrategy):
    def validate(
        self,
        dossier_documents: Dict[str, Dict[str, Any]],
        confidence_scores: Dict[str, float],
        confidence_threshold: float,
    ) -> QualityRuleResult:
        discrepancies: List[FieldDiscrepancy] = []
        confidence_passed = True
        for doc_code, score in confidence_scores.items():
            if score is not None and score < confidence_threshold:
                confidence_passed = False
                discrepancies.append(FieldDiscrepancy(
                    field_name="confidence_score",
                    expected_pattern=f">= {confidence_threshold}",
                    actual_value=str(score),
                    rule_description=f"El score de confianza del documento {doc_code} ({score:.2f}) est? por debajo del umbral ({confidence_threshold})",
                    severity="WARNING",
                    document_code=doc_code,
                ))
        return QualityRuleResult(
            is_valid=confidence_passed,
            discrepancies=discrepancies,
            confidence_passed=confidence_passed,
        )

    def get_field_definitions(self) -> List[dict]:
        return []
