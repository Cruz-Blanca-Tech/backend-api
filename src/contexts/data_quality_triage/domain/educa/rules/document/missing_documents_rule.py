from typing import List, Optional
from src.contexts.data_quality_triage.domain.shared.value_objects.field_discrepancy import FieldDiscrepancy
from src.contexts.data_quality_triage.domain.educa.value_objects.enriched_data import EnrichedFins, EnrichedDj, EnrichedDni

class MissingDocumentsRule:
    def evaluate(
        self,
        enriched_fins: Optional[EnrichedFins],
        enriched_dj: Optional[EnrichedDj],
        enriched_dnibe: Optional[EnrichedDni],
        enriched_dniap: Optional[EnrichedDni]
    ) -> List[FieldDiscrepancy]:
        
        discrepancies = []
        
        if not enriched_fins:
            discrepancies.append(self._create_discrepancy("Ficha de Inscripción (FINS)"))
        if not enriched_dj:
            discrepancies.append(self._create_discrepancy("Declaración Jurada (DJ)"))
        if not enriched_dnibe:
            discrepancies.append(self._create_discrepancy("DNI del Beneficiario (Niño/a)"))
        if not enriched_dniap:
            discrepancies.append(self._create_discrepancy("DNI del Apoderado"))
            
        return discrepancies
        
    def _create_discrepancy(self, doc_name: str) -> FieldDiscrepancy:
        return FieldDiscrepancy(
            field_name="documentos",
            expected_pattern="Presente",
            actual_value="Faltante",
            rule_description=f"Falta procesar o adjuntar el documento obligatorio: {doc_name}.",
            severity="ERROR",
            document_code="GLOBAL"
        )
