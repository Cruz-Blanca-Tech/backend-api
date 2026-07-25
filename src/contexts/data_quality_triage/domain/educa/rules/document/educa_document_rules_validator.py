from typing import List, Tuple

from src.contexts.data_quality_triage.domain.shared.value_objects.field_discrepancy import FieldDiscrepancy
from src.contexts.data_quality_triage.domain.educa.value_objects.document_code import EducaDocumentCode
from src.contexts.data_quality_triage.domain.educa.rules.document.dni_rules import (
    DniFormatRule, BeneficiaryDniCrosscheckRule, GuardianDniCrosscheckRule,
)
from src.contexts.data_quality_triage.domain.educa.rules.document.missing_documents_rule import MissingDocumentsRule


class EducaDocumentRulesValidator:
    """
    Ejecuta todas las reglas de validación cruzada de documentos para el flujo Educa.
    Recibe los objetos Enriched ya normalizados y retorna una tupla:
    (discrepancias, is_incomplete, has_document_errors)
    """

    _rules = [
        DniFormatRule,
        BeneficiaryDniCrosscheckRule,
        GuardianDniCrosscheckRule,
    ]

    def validate(
        self,
        enriched_docs: dict,
    ) -> Tuple[List[FieldDiscrepancy], bool, bool]:
        fins   = enriched_docs.get(EducaDocumentCode.FINS.value)
        dj     = enriched_docs.get(EducaDocumentCode.DJ.value)
        dnibe  = enriched_docs.get(EducaDocumentCode.DNI_BENEFICIARY.value)
        dniap  = enriched_docs.get(EducaDocumentCode.DNI_APODERADO.value)

        # 1. Regla de completitud (Short-circuit)
        missing_discrepancies = MissingDocumentsRule().evaluate(
            enriched_fins=fins, enriched_dj=dj,
            enriched_dnibe=dnibe, enriched_dniap=dniap,
        )
        if missing_discrepancies:
            return missing_discrepancies, True, False

        discrepancies: List[FieldDiscrepancy] = []

        # 2. Reglas de documento
        for RuleClass in self._rules:
            discrepancies.extend(
                RuleClass().evaluate(
                    enriched_fins=fins, enriched_dj=dj,
                    enriched_dnibe=dnibe, enriched_dniap=dniap,
                )
            )

        # Determinar si hay errores documentales específicos de OCR/Formato
        has_doc_errors = any(d.severity == "ERROR" for d in discrepancies)
        
        return discrepancies, False, has_doc_errors
