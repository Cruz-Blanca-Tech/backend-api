from typing import List
from src.contexts.data_quality_triage.domain.shared.value_objects.field_discrepancy import FieldDiscrepancy
from src.contexts.data_quality_triage.domain.shared.rules.base_rule import DomainRule
from src.contexts.data_quality_triage.domain.educa.value_objects.educa_inscription_dossier import EducaInscriptionDossier

class EducationRules(DomainRule):
    def evaluate(self, domain_entity: EducaInscriptionDossier) -> List[FieldDiscrepancy]:
        issues = []

        # Regla de dominio: el colegio es OBLIGATORIO y debe ser uno del maestro
        # MDM. Durante el procesamiento, el EducationDomainMapper (con el contexto
        # de colegios activos que carga el dossier_processor) normaliza el colegio
        # al nombre canónico de la base; si lo extraído no matchea ningún registro,
        # deja el campo en None. Durante la corrección el operador elige de la
        # lista (SchoolSelect), así que el valor siempre es un colegio de la base
        # o está vacío. Cualquiera de esos casos cae aquí y bloquea la aprobación.
        school_raw = domain_entity.education.school
        school = (school_raw or "").strip().lower()
        if not school or school in {"no registrada", "no registrado", "unknown", "ninguno", "n/a"}:
            issues.append(FieldDiscrepancy(
                field_name="education.school", expected_pattern="Colegio registrado en el maestro (MDM)",
                actual_value=school_raw or "(vacío)",
                rule_description="El colegio es obligatorio y debe ser uno de los registrados en el maestro de colegios. Seleccione el correcto de la lista.",
                severity="ERROR", document_code="DOMINIO"
            ))

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
