from typing import List
from src.contexts.data_quality_triage.domain.shared.value_objects.field_discrepancy import FieldDiscrepancy
from src.contexts.data_quality_triage.domain.shared.rules.base_rule import DomainRule
from src.contexts.data_quality_triage.domain.educa.value_objects.educa_inscription_dossier import EducaInscriptionDossier

class GuardianPresenceRule(DomainRule):
    def evaluate(self, domain_entity: EducaInscriptionDossier) -> List[FieldDiscrepancy]:
        issues = []
        guardian_dni = (domain_entity.related_adults.guardian_dni or "").strip()
        if not guardian_dni:
            issues.append(FieldDiscrepancy(
                field_name="related_adults.guardian", expected_pattern="DNI de 8 dígitos", actual_value="(vacío)",
                rule_description="No se ha asignado un Apoderado al expediente o no cuenta con DNI.", 
                severity="ERROR", document_code="DOMINIO"
            ))
        elif not (guardian_dni.isdigit() and len(guardian_dni) == 8):
            issues.append(FieldDiscrepancy(
                field_name="related_adults.guardian", expected_pattern="8 dígitos numéricos", actual_value=guardian_dni,
                rule_description=f"El DNI del apoderado asignado ('{guardian_dni}') debe tener exactamente 8 dígitos numéricos.", 
                severity="ERROR", document_code="DOMINIO"
            ))
        else:
            guardian = next((a for a in domain_entity.related_adults.adults if (a.dni or "").strip() == guardian_dni), None)
            if not guardian:
                issues.append(FieldDiscrepancy(
                    field_name="related_adults.guardian", expected_pattern="Adulto registrado", actual_value=guardian_dni,
                    rule_description=f"El DNI del apoderado ({guardian_dni}) no corresponde a ningún adulto registrado en el expediente.", 
                    severity="ERROR", document_code="DOMINIO"
                ))
            elif not guardian.full_name or not guardian.full_name.strip():
                issues.append(FieldDiscrepancy(
                    field_name="related_adults.guardian_name", expected_pattern="Nombre completo", actual_value="(vacío)",
                    rule_description=f"El apoderado asignado (DNI: {guardian_dni}) debe tener Nombre completo.", 
                    severity="ERROR", document_code="DOMINIO"
                ))
        return issues

class EmergencyContactRule(DomainRule):
    """
    Verifica que el contacto de emergencia haya sido resuelto a un adulto válido con DNI de 8 dígitos.
    """
    def evaluate(self, domain_entity: EducaInscriptionDossier) -> List[FieldDiscrepancy]:
        issues = []
        emergency_dni = (domain_entity.related_adults.emergency_contact_dni or "").strip()
        
        if not emergency_dni:
            issues.append(FieldDiscrepancy(
                field_name="related_adults.emergency_contact_dni", expected_pattern="DNI asignado", actual_value="(vacío)",
                rule_description="No se pudo asignar un contacto de emergencia a ninguno de los adultos.", 
                severity="ERROR", document_code="DOMINIO"
            ))
            return issues
            
        if not (emergency_dni.isdigit() and len(emergency_dni) == 8):
            issues.append(FieldDiscrepancy(
                field_name="related_adults.emergency_contact_dni", expected_pattern="8 dígitos numéricos", actual_value=emergency_dni,
                rule_description=f"El DNI del contacto de emergencia ('{emergency_dni}') debe tener exactamente 8 dígitos numéricos.", 
                severity="ERROR", document_code="DOMINIO"
            ))
            return issues

        adult_dnis = [(a.dni or "").strip() for a in domain_entity.related_adults.adults if a.dni]
        if emergency_dni not in adult_dnis:
            issues.append(FieldDiscrepancy(
                field_name="related_adults.emergency_contact_dni", expected_pattern="DNI de un adulto registrado", actual_value=str(emergency_dni),
                rule_description="El contacto de emergencia resuelto no corresponde a ningún adulto registrado.", 
                severity="ERROR", document_code="DOMINIO"
            ))
            
        return issues


class AdultsDniFormatRule(DomainRule):
    """
    Verifica que todo adulto registrado en el entorno familiar cuente obligatoriamente
    con un DNI de exactamente 8 dígitos numéricos y nombre completo.
    """
    def evaluate(self, domain_entity: EducaInscriptionDossier) -> List[FieldDiscrepancy]:
        issues = []
        for adult in domain_entity.related_adults.adults:
            label = adult.full_name or adult.relationship or "un familiar"
            dni = (adult.dni or "").strip()
            
            if not dni:
                issues.append(FieldDiscrepancy(
                    field_name="related_adults.adults",
                    expected_pattern="8 dígitos numéricos",
                    actual_value="(vacío)",
                    rule_description=f"El familiar '{label}' no tiene DNI registrado. El DNI es obligatorio para cada familiar.",
                    severity="ERROR",
                    document_code="DOMINIO"
                ))
            elif not (dni.isdigit() and len(dni) == 8):
                issues.append(FieldDiscrepancy(
                    field_name="related_adults.adults",
                    expected_pattern="8 dígitos numéricos",
                    actual_value=dni,
                    rule_description=f"El DNI '{dni}' del familiar '{label}' no es válido: debe tener exactamente 8 dígitos numéricos.",
                    severity="ERROR",
                    document_code="DOMINIO"
                ))

            if not (adult.full_name or "").strip():
                issues.append(FieldDiscrepancy(
                    field_name="related_adults.adults",
                    expected_pattern="Nombre completo",
                    actual_value="(vacío)",
                    rule_description=f"El familiar registrado ({adult.relationship}) debe tener Nombre completo.",
                    severity="ERROR",
                    document_code="DOMINIO"
                ))
        return issues


class FamilyDniUniquenessRule(DomainRule):
    """
    Verifica que cada persona del entorno familiar tenga un DNI único
    y que ninguno coincida con el DNI del beneficiario.
    """
    def evaluate(self, domain_entity: EducaInscriptionDossier) -> List[FieldDiscrepancy]:
        issues = []
        beneficiary_dni = (domain_entity.beneficiary.dni or "").strip()
        seen_dnis = {}

        for adult in domain_entity.related_adults.adults:
            ad_dni = (adult.dni or "").strip()
            if not ad_dni:
                continue

            # Verificar DNI duplicado entre familiares
            if ad_dni in seen_dnis:
                prev_adult = seen_dnis[ad_dni]
                prev_label = prev_adult.full_name or prev_adult.relationship or "un familiar"
                curr_label = adult.full_name or adult.relationship or "otro familiar"
                issues.append(FieldDiscrepancy(
                    field_name="related_adults.adults",
                    expected_pattern="DNI único por persona",
                    actual_value=ad_dni,
                    rule_description=f"El DNI {ad_dni} está duplicado entre '{prev_label}' y '{curr_label}'. Cada persona debe tener un DNI único.",
                    severity="ERROR",
                    document_code="DOMINIO"
                ))
            else:
                seen_dnis[ad_dni] = adult

            # Verificar conflicto con el DNI del beneficiario
            if beneficiary_dni and ad_dni == beneficiary_dni:
                issues.append(FieldDiscrepancy(
                    field_name="related_adults.adults",
                    expected_pattern="DNI diferente al del beneficiario",
                    actual_value=ad_dni,
                    rule_description=f"El DNI {ad_dni} del familiar '{adult.full_name or adult.relationship}' coincide con el del beneficiario.",
                    severity="ERROR",
                    document_code="DOMINIO"
                ))

        return issues

