from typing import List
from src.contexts.data_quality_triage.domain.shared.value_objects.field_discrepancy import FieldDiscrepancy
from src.contexts.data_quality_triage.domain.shared.rules.base_rule import DomainRule
from src.contexts.data_quality_triage.domain.educa.value_objects.educa_inscription_dossier import EducaInscriptionDossier


def _t(role) -> str:
    if not role: return "Familiar"
    r = str(role).upper()
    if r == "FATHER": return "Padre"
    if r == "MOTHER": return "Madre"
    if r == "SIBLING": return "Hermano(a)"
    if r == "GRANDPARENT": return "Abuelo(a)"
    return "Familiar"

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

        contact_adult = next((a for a in domain_entity.related_adults.adults if (a.dni or "").strip() == emergency_dni), None)
        if not contact_adult:
            issues.append(FieldDiscrepancy(
                field_name="related_adults.emergency_contact_dni", expected_pattern="DNI de un adulto registrado", actual_value=str(emergency_dni),
                rule_description="El contacto de emergencia resuelto no corresponde a ningún adulto registrado.", 
                severity="ERROR", document_code="DOMINIO"
            ))
        else:
            phone = (contact_adult.phone or "").strip()
            if not phone:
                issues.append(FieldDiscrepancy(
                    field_name="related_adults.adults", expected_pattern="Número de teléfono", actual_value="(vacío)",
                    rule_description=f"El contacto de emergencia ({contact_adult.full_name or emergency_dni}) no tiene un número de teléfono registrado. Es obligatorio.", 
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
            label = adult.full_name or _t(adult.relationship) or "un familiar"
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
                    rule_description=f"El familiar registrado ({_t(adult.relationship)}) debe tener Nombre completo.",
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
                prev_label = prev_adult.full_name or _t(prev_adult.relationship) or "un familiar"
                curr_label = adult.full_name or _t(adult.relationship) or "otro familiar"
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
                    rule_description=f"El DNI {ad_dni} del familiar '{adult.full_name or _t(adult.relationship)}' coincide con el del beneficiario.",
                    severity="ERROR",
                    document_code="DOMINIO"
                ))

        return issues


class DjFinsSignerCoherenceRule(DomainRule):
    """
    Verifica que el adulto que firmó la Declaración Jurada (DJ) sea el mismo 
    que el Apoderado principal registrado en la ficha FINS.
    """
    def evaluate(self, domain_entity: EducaInscriptionDossier) -> List[FieldDiscrepancy]:
        issues = []
        fins_guardian = domain_entity.related_adults.fins_guardian_dni
        dj_signer = domain_entity.related_adults.dj_signer_dni
        
        if fins_guardian and dj_signer and fins_guardian != dj_signer:
            issues.append(FieldDiscrepancy(
                field_name="related_adults.dj_signer",
                expected_pattern="Coincidencia entre FINS y DJ",
                actual_value=f"DJ: {dj_signer} vs FINS: {fins_guardian}",
                rule_description="El adulto que firma la Declaración Jurada (DJ) no coincide con el Apoderado registrado en la Ficha FINS. Revisa si esto es válido (ej. un padre firmó la DJ pero la madre es apoderada).",
                severity="WARNING",
                document_code="DOMINIO"
            ))
            
        return issues

class UniqueParentRoleRule(DomainRule):
    """
    Verifica que no haya ms de un Padre o ms de una Madre en el expediente.
    """
    def evaluate(self, domain_entity: EducaInscriptionDossier) -> List[FieldDiscrepancy]:
        issues = []
        fathers = [a for a in domain_entity.related_adults.adults if str(a.relationship).upper() == "FATHER"]
        mothers = [a for a in domain_entity.related_adults.adults if str(a.relationship).upper() == "MOTHER"]
        
        if len(fathers) > 1:
            names = ", ".join(a.full_name or "Desconocido" for a in fathers)
            issues.append(FieldDiscrepancy(
                field_name="related_adults.adults",
                expected_pattern="Mximo un (1) Padre",
                actual_value=f"{len(fathers)} Padres: {names}",
                rule_description="Existen mltiples personas etiquetadas como 'Padre' en el expediente. Solo puede haber uno.",
                severity="ERROR",
                document_code="DOMINIO"
            ))
            
        if len(mothers) > 1:
            names = ", ".join(a.full_name or "Desconocido" for a in mothers)
            issues.append(FieldDiscrepancy(
                field_name="related_adults.adults",
                expected_pattern="Mximo una (1) Madre",
                actual_value=f"{len(mothers)} Madres: {names}",
                rule_description="Existen mltiples personas etiquetadas como 'Madre' en el expediente. Solo puede haber una.",
                severity="ERROR",
                document_code="DOMINIO"
            ))
            
        return issues


class ParentLastNameCoherenceRule(DomainRule):
    """
    Verifica que los apellidos del Padre y de la Madre tengan sentido
    respecto a los apellidos del Beneficiario, tolerando errores de OCR.
    """
    def evaluate(self, domain_entity: EducaInscriptionDossier) -> List[FieldDiscrepancy]:
        import re
        from typing import List
        issues = []
        
        ben_name = f"{domain_entity.beneficiary.first_name or ''} {domain_entity.beneficiary.last_name or ''}".strip()
        
        def _normalize_name_for_match(name: str) -> str:
            name = name.lower()
            name = re.sub(r'[^a-z0-9\s]', '', name)
            return name
            
        ben_norm = _normalize_name_for_match(ben_name)
        ben_words = ben_norm.split()
        if len(ben_words) < 2:
            return issues
            
        ben_last_names = ben_words[-2:] if len(ben_words) >= 3 else [ben_words[-1]]
        
        for adult in domain_entity.related_adults.adults:
            role = str(adult.relationship).upper()
            if role in ["FATHER", "MOTHER"] and adult.full_name:
                adult_norm = _normalize_name_for_match(adult.full_name)
                adult_words = adult_norm.split()
                
                # Check with exact substring match or fuzzy matching for OCR typos
                import difflib
                found_match = False
                for last_name in ben_last_names:
                    if last_name in adult_norm:
                        found_match = True
                        break
                    for word in adult_words:
                        if difflib.SequenceMatcher(None, last_name, word).ratio() > 0.80:
                            found_match = True
                            break
                    if found_match:
                        break

                if not found_match:
                    label_rol = "el Padre" if role == "FATHER" else "la Madre"
                    issues.append(FieldDiscrepancy(
                        field_name="related_adults.adults",
                        expected_pattern="Coincidencia parcial de apellidos",
                        actual_value=f"Beneficiario: {ben_name} | Adulto: {adult.full_name}",
                        rule_description=f"Los apellidos d{label_rol} ('{adult.full_name}') no parecen coincidir con los del beneficiario ('{ben_name}'). Verifique posibles errores del OCR.",
                        severity="WARNING",
                        document_code="DOMINIO"
                    ))
                    
        return issues

class DjSignerPresenceRule(DomainRule):
    """
    Verifica que la Declaración Jurada (DJ) tenga un firmante extraído.
    """
    def evaluate(self, domain_entity: EducaInscriptionDossier) -> List[FieldDiscrepancy]:
        issues = []
        dj_signer = (domain_entity.related_adults.dj_signer_dni or "").strip()
        
        if not dj_signer:
            issues.append(FieldDiscrepancy(
                field_name="related_adults.dj_signer",
                expected_pattern="DNI del firmante",
                actual_value="(vacío)",
                rule_description="No se detectó el DNI del firmante en la Declaración Jurada (DJ). Verifique la firma en la imagen y asegúrese de que el documento esté firmado por el apoderado.",
                severity="WARNING",
                document_code="DOMINIO"
            ))
            
        return issues

