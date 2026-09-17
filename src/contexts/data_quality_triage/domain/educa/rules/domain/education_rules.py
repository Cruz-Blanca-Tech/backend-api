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
            
        valid_grades = {
            'INICIAL_3', 'INICIAL_4', 'INICIAL_5', 
            '1RO_PRIMARIA', '2DO_PRIMARIA', '3RO_PRIMARIA', '4TO_PRIMARIA', '5TO_PRIMARIA', '6TO_PRIMARIA',
            '1RO_SECUNDARIA', '2DO_SECUNDARIA', '3RO_SECUNDARIA', '4TO_SECUNDARIA', '5TO_SECUNDARIA',
            'SUPERIOR', 'NINGUNO'
        }
        
        if domain_entity.education.grade and domain_entity.education.grade not in valid_grades:
            issues.append(FieldDiscrepancy(
                field_name="education.grade", expected_pattern="Grado escolar válido", actual_value=domain_entity.education.grade,
                rule_description="El grado escolar extraído no coincide con la lista estandarizada. Por favor, selecciona el correcto del menú desplegable.", 
                severity="ERROR", document_code="DOMINIO"
            ))
            
        return issues
