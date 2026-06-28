from typing import List
from src.contexts.data_quality_triage.domain.shared.value_objects.field_discrepancy import FieldDiscrepancy
from src.contexts.data_quality_triage.domain.shared.rules.base_rule import DomainRule
from src.contexts.data_quality_triage.domain.educa.value_objects.educa_inscription_dossier import EducaInscriptionDossier

class MedicalRules(DomainRule):
    def evaluate(self, domain_entity: EducaInscriptionDossier) -> List[FieldDiscrepancy]:
        issues = []
        if domain_entity.medical.has_been_hospitalized and not domain_entity.medical.hospitalization_reason:
             issues.append(FieldDiscrepancy(
                field_name="medical.hospitalization_reason", expected_pattern="Motivo de hospitalización", actual_value="(vacío)",
                rule_description="Si estuvo hospitalizado, debe especificar el motivo.", 
                severity="ERROR", document_code="DOMINIO"
            ))
        return issues
