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
    def evaluate(self, domain_entity: EducaInscriptionDossier) -> List[FieldDiscrepancy]:
        issues = []
        from src.contexts.data_quality_triage.domain.shared.value_objects.phone_number import PhoneNumber
        
        valid_phones = []
        for adult in domain_entity.related_adults.adults:
            if adult.phone and PhoneNumber.is_valid(adult.phone):
                valid_phones.append(adult.phone)
                
        if not valid_phones:
            issues.append(FieldDiscrepancy(
                field_name="related_adults.phone", expected_pattern="Al menos 1 teléfono válido", actual_value="(inválido o vacío)",
                rule_description="Debe existir al menos un número de emergencia válido (7-15 dígitos, opcionalmente con prefijo '+') registrado para los adultos.", 
                severity="ERROR", document_code="DOMINIO"
            ))
        return issues
