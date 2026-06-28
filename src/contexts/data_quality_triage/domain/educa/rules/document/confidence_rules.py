from typing import List, Any
from src.contexts.data_quality_triage.domain.shared.value_objects.field_discrepancy import FieldDiscrepancy
from src.contexts.data_quality_triage.domain.shared.rules.base_rule import DocumentRule

class OcrConfidenceRule(DocumentRule):
    """Valida que la calidad de extracción del OCR supere el umbral mínimo por documento."""
    
    def __init__(self, confidence_scores: dict, confidence_threshold: float):
        self.confidence_scores = confidence_scores
        self.confidence_threshold = confidence_threshold
        
    def evaluate(self, enriched_fins: Any = None, enriched_dj: Any = None, **kwargs) -> List[FieldDiscrepancy]:
        discrepancies = []
        for doc_code, score in self.confidence_scores.items():
            if score is not None and score < self.confidence_threshold:
                discrepancies.append(FieldDiscrepancy(
                    field_name="general_confidence",
                    expected_pattern=f">= {self.confidence_threshold}",
                    actual_value=str(score),
                    rule_description=f"La calidad del escaneo para el documento {doc_code} es demasiado baja. Por favor verifique los datos manualmente.",
                    severity="WARNING",
                    document_code=doc_code
                ))
        return discrepancies
