from typing import List, Any, Dict, Union
from src.contexts.data_quality_triage.domain.shared.value_objects.field_discrepancy import FieldDiscrepancy
from src.contexts.data_quality_triage.domain.shared.rules.base_rule import DocumentRule

class OcrConfidenceRule(DocumentRule):
    """
    Valida que la calidad de extracción del OCR supere el umbral mínimo por documento.

    El umbral puede ser:
      - un float global que se aplica a todos los documentos, o
      - un dict {document_code: umbral} para calibrar por tipo de documento
        (ej. DJ 0.55, FINS 0.60, DNIAP/DNIBE 0.65).

    Con dict, los documentos sin umbral definido NO se evalúan (se omiten).
    Con float, todos los documentos se comparan contra el mismo umbral.
    Los scores None se ignoran (no hay certeza de lectura, la regla no inventa).
    """

    def __init__(self, confidence_scores: dict, confidence_threshold: Union[float, Dict[str, float]]):
        self.confidence_scores = confidence_scores or {}
        self.confidence_threshold = confidence_threshold

    def _threshold_for(self, doc_code: str) -> Union[float, None]:
        if isinstance(self.confidence_threshold, dict):
            return self.confidence_threshold.get(doc_code)
        return self.confidence_threshold

    def evaluate(self, enriched_fins: Any = None, enriched_dj: Any = None, **kwargs) -> List[FieldDiscrepancy]:
        discrepancies = []
        for doc_code, score in self.confidence_scores.items():
            threshold = self._threshold_for(doc_code)
            if threshold is None:
                continue
            if score is not None and score < threshold:
                discrepancies.append(FieldDiscrepancy(
                    field_name="general_confidence",
                    expected_pattern=f">= {threshold}",
                    actual_value=str(score),
                    rule_description=f"La calidad del escaneo para el documento {doc_code} es demasiado baja (umbral mínimo {threshold}). Por favor verifique los datos manualmente.",
                    severity="WARNING",
                    document_code=doc_code
                ))
        return discrepancies