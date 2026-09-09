from typing import List, Any
from src.contexts.data_quality_triage.domain.shared.value_objects.field_discrepancy import FieldDiscrepancy
from src.contexts.data_quality_triage.domain.shared.rules.base_rule import DocumentRule
from src.contexts.data_quality_triage.domain.educa.value_objects.document_code import EducaDocumentCode

class RequiredDocumentsRule(DocumentRule):
    """
    Valida que todos los documentos obligatorios para el expediente de Inscripción EDUCA
    estén presentes (FINS, DJ, DNIBE, DNIAP).
    Si alguno falta, genera una discrepancia bloqueante con severity="ERROR".
    """

    REQUIRED_DOCS = [
        (EducaDocumentCode.FINS.value, "Ficha de Inscripción", "enriched_fins"),
        (EducaDocumentCode.DJ.value, "Declaración Jurada", "enriched_dj"),
        (EducaDocumentCode.DNI_BENEFICIARY.value, "DNI del Beneficiario", "enriched_dnibe"),
        (EducaDocumentCode.DNI_APODERADO.value, "DNI del Apoderado", "enriched_dniap"),
    ]

    def evaluate(
        self,
        enriched_fins: Any = None,
        enriched_dj: Any = None,
        enriched_dnibe: Any = None,
        enriched_dniap: Any = None,
        **kwargs
    ) -> List[FieldDiscrepancy]:
        discrepancies: List[FieldDiscrepancy] = []

        doc_map = {
            "enriched_fins": enriched_fins,
            "enriched_dj": enriched_dj,
            "enriched_dnibe": enriched_dnibe,
            "enriched_dniap": enriched_dniap,
        }

        for doc_code, doc_name, param_name in self.REQUIRED_DOCS:
            if not doc_map.get(param_name):
                discrepancies.append(FieldDiscrepancy(
                    field_name=f"documents.{doc_code}",
                    expected_pattern=f"Documento {doc_name} ({doc_code}) adjunto",
                    actual_value="Faltante",
                    rule_description=f"Falta el documento obligatorio: {doc_name} ({doc_code}). Debe adjuntar el documento para continuar.",
                    severity="ERROR",
                    document_code=doc_code
                ))

        return discrepancies
