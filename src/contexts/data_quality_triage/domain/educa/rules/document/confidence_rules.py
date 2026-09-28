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
        low_confidence_docs = []

        for doc_code, score in self.confidence_scores.items():
            threshold = self._threshold_for(doc_code)
            if threshold is None:
                continue
            if score is not None and score < threshold:
                low_confidence_docs.append({
                    "code": doc_code,
                    "score": score,
                    "threshold": threshold
                })

        if low_confidence_docs:
            # Build consolidated message
            doc_details = ", ".join(
                f"{d['code']} ({d['score']:.2f} < {d['threshold']})"
                for d in low_confidence_docs
            )
            discrepancies.append(FieldDiscrepancy(
                field_name="general_confidence",
                expected_pattern="All documents >= their thresholds",
                actual_value=f"{len(low_confidence_docs)} document(s) below threshold",
                rule_description=(
                    f"Se detectaron {len(low_confidence_docs)} documento(s) con calidad de escaneo baja: "
                    f"{doc_details}. Por favor revise la información y continúe si considera que los datos son correctos."
                ),
                severity="WARNING",
                document_code="GENERAL"
            ))

        return discrepancies