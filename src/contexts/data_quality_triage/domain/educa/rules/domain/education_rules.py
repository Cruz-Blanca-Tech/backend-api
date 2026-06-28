from typing import List
from src.contexts.data_quality_triage.domain.shared.value_objects.field_discrepancy import FieldDiscrepancy
from src.contexts.data_quality_triage.domain.shared.rules.base_rule import DomainRule
from src.contexts.data_quality_triage.domain.educa.value_objects.educa_inscription_dossier import EducaInscriptionDossier

class EducationRules(DomainRule):
    def evaluate(self, domain_entity: EducaInscriptionDossier) -> List[FieldDiscrepancy]:
        issues = []
        if domain_entity.education.knows_read and not domain_entity.education.grade:
            issues.append(FieldDiscrepancy(
                field_name="education.grade", expected_pattern="Grado escolar", actual_value="(vacío)",
                rule_description="Si sabe leer, debe tener un grado escolar asignado.", 
                severity="ERROR", document_code="DOMINIO"
            ))
        return issues
