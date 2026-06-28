from typing import List

from src.contexts.data_quality_triage.domain.shared.value_objects.field_discrepancy import FieldDiscrepancy
from src.contexts.data_quality_triage.domain.educa.value_objects.document_code import EducaDocumentCode
from src.contexts.data_quality_triage.domain.educa.rules.document.dni_rules import (
    DniFormatRule, BeneficiaryDniCrosscheckRule, GuardianDniCrosscheckRule,
)


class EducaDocumentRulesValidator:
    """
    Ejecuta todas las reglas de validación cruzada de documentos para el flujo Educa.
    Recibe los objetos Enriched ya normalizados y retorna las discrepancias encontradas.
    """

    _rules = [
        DniFormatRule,
        BeneficiaryDniCrosscheckRule,
        GuardianDniCrosscheckRule,
    ]

    def validate(
        self,
        enriched_docs: dict,
    ) -> List[FieldDiscrepancy]:
        fins   = enriched_docs.get(EducaDocumentCode.FINS.value)
        dj     = enriched_docs.get(EducaDocumentCode.DJ.value)
        dnibe  = enriched_docs.get(EducaDocumentCode.DNI_BENEFICIARY.value)
        dniap  = enriched_docs.get(EducaDocumentCode.DNI_APODERADO.value)

        discrepancies: List[FieldDiscrepancy] = []



        # Reglas de documento
        for RuleClass in self._rules:
            discrepancies.extend(
                RuleClass().evaluate(
                    enriched_fins=fins, enriched_dj=dj,
                    enriched_dnibe=dnibe, enriched_dniap=dniap,
                )
            )

        return discrepancies
