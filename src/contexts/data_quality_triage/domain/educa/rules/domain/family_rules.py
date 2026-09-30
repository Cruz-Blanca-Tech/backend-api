import re
from typing import List
from src.contexts.data_quality_triage.domain.shared.value_objects.field_discrepancy import FieldDiscrepancy
from src.contexts.data_quality_triage.domain.shared.rules.base_rule import DomainRule
from src.contexts.data_quality_triage.domain.educa.value_objects.educa_inscription_dossier import EducaInscriptionDossier


def _is_valid_phone(value) -> bool:
    """Teléfono válido con el mismo formato que el maestro (value object Phone:
    ^\\+?[0-9\\s\\-()]{7,20}$). Vacío o formato raro → False."""
    v = (value or "").strip()
    if not v:
        return False
    return bool(re.match(r"^\+?[0-9\s\-()]{7,20}$", v))


def _t(role) -> str:
    if not role: return "Familiar"
    r = str(role).upper()
    if r == "FATHER": return "Padre"
    if r == "MOTHER": return "Madre"
    if r == "SIBLING": return "Hermano(a)"
    if r == "GRANDPARENT": return "Abuelo(a)"
    return "Familiar"


def _as_str(value) -> str:
    """Normaliza defensivamente un valor extraído a str (o '').

    Las reglas de dominio NUNCA deben crashear por datos raros del OCR (dict,
    números, None): si el valor no es una cadena útil, se degrada a ''.
    """
    if value is None:
        return ""
    try:
        return str(value).strip()
    except Exception:
        return ""

class GuardianPresenceRule(DomainRule):
    def evaluate(self, domain_entity: EducaInscriptionDossier) -> List[FieldDiscrepancy]:
        issues = []
        guardian_dni = (domain_entity.related_adults.guardian_dni or "").strip()
        if not guardian_dni:
            issues.append(FieldDiscrepancy(
                field_name="related_adults.guardian", expected_pattern="DNI de 8 dígitos", actual_value="(vacío)",
                rule_description="No se ha asignado un Apoderado al expediente o no cuenta con DNI.", 
                severity="ERROR", document_code="DOMINIO",
                navigation_hint="contactos_apoderados"
            ))
        elif not (guardian_dni.isdigit() and len(guardian_dni) == 8):
            issues.append(FieldDiscrepancy(
                field_name="related_adults.guardian", expected_pattern="8 dígitos numéricos", actual_value=guardian_dni,
                rule_description=f"El DNI del apoderado asignado ('{guardian_dni}') debe tener exactamente 8 dígitos numéricos.", 
                severity="ERROR", document_code="DOMINIO",
                navigation_hint="contactos_apoderados"
            ))
        else:
            guardian = next((a for a in domain_entity.related_adults.adults if (a.dni or "").strip() == guardian_dni), None)
            if not guardian:
                issues.append(FieldDiscrepancy(
                    field_name="related_adults.guardian", expected_pattern="Adulto registrado", actual_value=guardian_dni,
                    rule_description=f"El DNI del apoderado ({guardian_dni}) no corresponde a ningún adulto registrado en el expediente.", 
                    severity="ERROR", document_code="DOMINIO",
                    navigation_hint="contactos_apoderados"
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
                severity="ERROR", document_code="DOMINIO",
                navigation_hint="contactos_apoderados"
            ))
            return issues
            
        if not (emergency_dni.isdigit() and len(emergency_dni) == 8):
            issues.append(FieldDiscrepancy(
                field_name="related_adults.emergency_contact_dni", expected_pattern="8 dígitos numéricos", actual_value=emergency_dni,
                rule_description=f"El DNI del contacto de emergencia ('{emergency_dni}') debe tener exactamente 8 dígitos numéricos.", 
                severity="ERROR", document_code="DOMINIO",
                navigation_hint="contactos_apoderados"
            ))
            return issues

        contact_adult = next((a for a in domain_entity.related_adults.adults if (a.dni or "").strip() == emergency_dni), None)
        if not contact_adult:
            issues.append(FieldDiscrepancy(
                field_name="related_adults.emergency_contact_dni", expected_pattern="DNI de un adulto registrado", actual_value=str(emergency_dni),
                rule_description="El contacto de emergencia resuelto no corresponde a ningún adulto registrado.", 
                severity="ERROR", document_code="DOMINIO",
                navigation_hint="contactos_apoderados"
            ))
        else:
            phone = (contact_adult.phone or "").strip()
            if not _is_valid_phone(phone):
                issues.append(FieldDiscrepancy(
                    field_name="related_adults.adults", expected_pattern="Número de teléfono válido (7–20 dígitos)", actual_value=phone or "(vacío)",
                    rule_description=f"El contacto de emergencia ({contact_adult.full_name or emergency_dni}) no tiene un número de teléfono válido. Es obligatorio: el número de contacto debe tener entre 7 y 20 dígitos (p. ej. 9XXXXXXXX).", 
                    severity="ERROR", document_code="DOMINIO",
                    navigation_hint="contactos_apoderados"
                ))
            
        return issues


class AdultsDniFormatRule(DomainRule):
    """
    Verifica que todo adulto registrado en el entorno familiar cuente obligatoriamente
    con un DNI de exactamente 8 dígitos numéricos y nombre completo.
    """
    def evaluate(self, domain_entity: EducaInscriptionDossier) -> List[FieldDiscrepancy]:
        issues = []
        guardian_dni = (domain_entity.related_adults.guardian_dni or "").strip()
        for adult in domain_entity.related_adults.adults:
            dni = (adult.dni or "").strip()
            is_guardian = bool(dni and guardian_dni and dni == guardian_dni)
            role_label = _t(adult.relationship) or "Familiar"
            if is_guardian:
                role_ctx = f"{role_label}, Apoderado, DNI: {dni}"
            elif dni:
                role_ctx = f"{role_label}, DNI: {dni}"
            else:
                role_ctx = role_label
            label = (adult.full_name or "").strip() or role_ctx
            
            if not dni:
                issues.append(FieldDiscrepancy(
                    field_name="related_adults.adults",
                    expected_pattern="8 dígitos numéricos",
                    actual_value="(vacío)",
                    rule_description=f"El familiar '{label}' no tiene DNI registrado. El DNI es obligatorio para cada familiar.",
                    severity="ERROR",
                    document_code="DOMINIO",
                    navigation_hint="contactos_apoderados"
                ))
            elif not (dni.isdigit() and len(dni) == 8):
                issues.append(FieldDiscrepancy(
                    field_name="related_adults.adults",
                    expected_pattern="8 dígitos numéricos",
                    actual_value=dni,
                    rule_description=f"El DNI '{dni}' del familiar '{label}' no es válido: debe tener exactamente 8 dígitos numéricos.",
                    severity="ERROR",
                    document_code="DOMINIO",
                    navigation_hint="contactos_apoderados"
                ))

            if not (adult.full_name or "").strip():
                issues.append(FieldDiscrepancy(
                    field_name="related_adults.adults",
                    expected_pattern="Nombre completo",
                    actual_value="(vacío)",
                    rule_description=f"El familiar registrado ({role_ctx}) debe tener Nombre completo.",
                    severity="ERROR",
                    document_code="DOMINIO",
                    navigation_hint="contactos_apoderados"
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
        # Acceso defensivo: si el expediente no trae FINS/DJ (o vienen valores
        # raros del OCR), no crashear — degradar a '' y evaluar lo que haya.
        fins_guardian = _as_str(getattr(domain_entity.related_adults, "fins_guardian_dni", None))
        dj_signer = _as_str(getattr(domain_entity.related_adults, "dj_signer_dni", None))

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


class ParentPresenceRule(DomainRule):
    """
    Verifica que el expediente tenga registrado AL MENOS un Padre o una Madre.

    Solo emite advertencia si no se detectó ni al Padre ni a la Madre (por ejemplo,
    cuando el OCR solo dejó familiares como 'OTHER' o no extrajo progenitores).
    Si ya cuenta con Padre o con Madre (familia monoparental), no emite advertencia.
    """
    def evaluate(self, domain_entity: EducaInscriptionDossier) -> List[FieldDiscrepancy]:
        issues = []
        fathers = [a for a in domain_entity.related_adults.adults if str(a.relationship).upper() == "FATHER"]
        mothers = [a for a in domain_entity.related_adults.adults if str(a.relationship).upper() == "MOTHER"]

        if len(fathers) == 0 and len(mothers) == 0:
            issues.append(FieldDiscrepancy(
                field_name="related_adults.adults",
                expected_pattern="Al menos un Padre o una Madre",
                actual_value="Sin Padre ni Madre registrados",
                rule_description="No se detectó ni al Padre ni a la Madre del beneficiario en los documentos. Revise si hay un familiar que deba ser etiquetado como Padre o Madre.",
                severity="WARNING",
                document_code="DOMINIO",
                navigation_hint="contactos_apoderados",
            ))

        return issues


class ParentLastNameCoherenceRule(DomainRule):
    """
    Verifica que los apellidos del Padre y de la Madre tengan sentido
    respecto a los apellidos del Beneficiario.

    El apellido del Padre y/o de la Madre DEBE coincidir con al menos
    uno de los apellidos del beneficiario. Si no hay coincidencia, es
    un ERROR: el operador debe corregirlo (OCR mal leído, rol mal
    asignado, familiar equivocado). NO es una advertencia.

    Ahora SIEMPRE se ejecuta (incluso si hay múltiples Padres/Madres):
    - Si hay duplicados, UniqueParentRoleRule ya emite ERROR.
    - Esta regla emite ERROR por cada padre/madre cuyos apellidos no coincidan,
      añadiendo contexto si hay duplicados.
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
        
        # Contar padres/madres para añadir contexto si hay duplicados
        fathers = [a for a in domain_entity.related_adults.adults if str(a.relationship).upper() == "FATHER"]
        mothers = [a for a in domain_entity.related_adults.adults if str(a.relationship).upper() == "MOTHER"]
        multi_father = len(fathers) > 1
        multi_mother = len(mothers) > 1
        
        for adult in domain_entity.related_adults.adults:
            role = str(adult.relationship).upper()
            if role in ["FATHER", "MOTHER"] and adult.full_name:
                # Ya NO se salta si hay múltiples: se evalúa cada uno y se avisa.
                # El ERROR por duplicados lo emite UniqueParentRoleRule; aquí
                # complementamos con ERROR de coherencia de apellidos.
                
                adult_norm = _normalize_name_for_match(adult.full_name)
                adult_words = adult_norm.split()
                
                # Basta con que UNO de los apellidos del beneficiario aparezca
                # en el nombre del adulto (exacto o con un parecido fuzzy alto)
                # para considerar la familia coherente.
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
                    contexto_duplicados = ""
                    if (role == "FATHER" and multi_father) or (role == "MOTHER" and multi_mother):
                        contexto_duplicados = " Además, hay múltiples personas con este rol (ver error de duplicados)."
                    issues.append(FieldDiscrepancy(
                        field_name="related_adults.adults",
                        expected_pattern="Coincidencia de apellidos (al menos uno)",
                        actual_value=f"Beneficiario: {ben_name} | Adulto: {adult.full_name}",
                        rule_description=f"Los apellidos d{label_rol} ('{adult.full_name}') no coinciden con los del beneficiario ('{ben_name}'). El apellido del padre/madre debe coincidir con al menos uno del beneficiario. Verifique errores del OCR o rol mal asignado.{contexto_duplicados}",
                        severity="ERROR",
                        document_code="DOMINIO"
                    ))
                    
        return issues

class DjSignerPresenceRule(DomainRule):
    """
    Verifica que la Declaración Jurada (DJ) tenga un firmante extraído.
    """
    def evaluate(self, domain_entity: EducaInscriptionDossier) -> List[FieldDiscrepancy]:
        issues = []
        dj_signer = _as_str(getattr(domain_entity.related_adults, "dj_signer_dni", None))
        
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

