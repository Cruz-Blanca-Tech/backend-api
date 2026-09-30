from typing import List, Any, Dict, Union
from src.contexts.data_quality_triage.domain.shared.value_objects.field_discrepancy import FieldDiscrepancy
from src.contexts.data_quality_triage.domain.shared.rules.base_rule import DocumentRule


# Nombres que el operador entiende para cada documento. El mensaje al usuario
# nunca muestra los códigos internos (DNIBE, DNIAP…) ni los puntajes de
# confianza: el operador no puede verificar un 0.54 contra un 0.65, solo puede
# mirar la imagen y decidir si lo que leyó está bien.
_NOMBRES_DOCUMENTO = {
    "FINS": "la ficha de inscripción",
    "DJ": "la declaración jurada",
    "DNIBE": "la copia del DNI del niño",
    "DNIAP": "la copia del DNI del apoderado",
}

# Como un solo documento puede repetir su nombre (p. ej. dos PDFs de la DJ), se
# listan los nombres únicos en el orden en que aparecen.
def _nombres_amigables(codigos) -> str:
    nombres: List[str] = []
    for codigo in codigos:
        nombre = _NOMBRES_DOCUMENTO.get(str(codigo).upper(), f"el documento {codigo}")
        if nombre not in nombres:
            nombres.append(nombre)
    if len(nombres) == 1:
        return nombres[0]
    return ", ".join(nombres[:-1]) + " y " + nombres[-1]


class OcrConfidenceRule(DocumentRule):
    """
    Valida que la calidad de extracción del OCR supere el umbral mínimo por documento.

    El umbral puede ser:
      - un float global que se aplica a todos los documentos, o
      - un dict {document_code: umbral} para calibrar por tipo de documento
        (ej. FINS 0.60, DNIAP/DNIBE 0.65).

    La Declaración Jurada (DJ) se excluye del umbral de confianza general porque
    es un documento de respaldo legal cuya validez se asegura mediante presencia
    de documento, presencia de firmante y validación cruzada de DNIs contra FINS,
    DNIBE y DNIAP.
    """

    EXCLUDED_DOC_CODES = {"DJ"}

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
            if str(doc_code).upper() in self.EXCLUDED_DOC_CODES:
                continue
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
            codigos = [d["code"] for d in low_confidence_docs]
            documentos = _nombres_amigables(codigos)
            if len(codigos) == 1:
                descripcion = (
                    f"La IA leyó con poca claridad {documentos}. Revisá la imagen y "
                    f"confirmá que los datos estén bien antes de continuar."
                )
            else:
                descripcion = (
                    f"La IA leyó con poca claridad {documentos}. Revisá esas imágenes y "
                    f"confirmá que los datos estén bien antes de continuar."
                )
            discrepancies.append(FieldDiscrepancy(
                field_name="general_confidence",
                expected_pattern="Documentos legibles",
                actual_value=f"{len(codigos)} documento(s) por revisar",
                rule_description=descripcion,
                severity="WARNING",
                document_code="GENERAL"
            ))

        return discrepancies