from typing import List
from src.contexts.data_quality_triage.domain.shared.value_objects.field_discrepancy import FieldDiscrepancy
from src.contexts.data_quality_triage.domain.shared.rules.base_rule import DomainRule
from src.contexts.data_quality_triage.domain.educa.value_objects.educa_inscription_dossier import EducaInscriptionDossier

class GuardianPresenceRule(DomainRule):
    def evaluate(self, domain_entity: EducaInscriptionDossier) -> List[FieldDiscrepancy]:
        issues = []
        if not domain_entity.related_adults.guardian_dni:
            issues.append(FieldDiscrepancy(
                field_name="related_adults.guardian", expected_pattern="DNI asignado", actual_value="(vacío)",
                rule_description="No se ha asignado un Apoderado (guardian) al dossier por su DNI.", 
                severity="ERROR", document_code="DOMINIO"
            ))
        else:
            guardian = next((a for a in domain_entity.related_adults.adults if a.dni == domain_entity.related_adults.guardian_dni), None)
            if not guardian or not guardian.full_name:
                issues.append(FieldDiscrepancy(
                    field_name="related_adults.guardian_name", expected_pattern="Nombre completo", actual_value="(vacío)",
                    rule_description=f"El apoderado asignado (DNI: {domain_entity.related_adults.guardian_dni}) debe estar registrado y tener Nombre.", 
                    severity="ERROR", document_code="DOMINIO"
                ))
        return issues

class EmergencyContactRule(DomainRule):
    """
    Verifica que el contacto de emergencia haya sido resuelto a un adulto válido.
    """
    def evaluate(self, domain_entity: EducaInscriptionDossier) -> List[FieldDiscrepancy]:
        issues = []
        emergency_dni = domain_entity.related_adults.emergency_contact_dni
        
        if not emergency_dni:
            issues.append(FieldDiscrepancy(
                field_name="related_adults.emergency_contact_dni", expected_pattern="DNI asignado", actual_value="(vacío)",
                rule_description="No se pudo asignar un contacto de emergencia a ninguno de los adultos.", 
                severity="ERROR", document_code="DOMINIO"
            ))
            return issues
            
        adult_dnis = [a.dni for a in domain_entity.related_adults.adults if a.dni]
        if emergency_dni not in adult_dnis:
            issues.append(FieldDiscrepancy(
                field_name="related_adults.emergency_contact_dni", expected_pattern="DNI de un adulto registrado", actual_value=str(emergency_dni),
                rule_description="El contacto de emergencia resuelto no corresponde a ningún adulto registrado.", 
                severity="ERROR", document_code="DOMINIO"
            ))
            
        return issues
