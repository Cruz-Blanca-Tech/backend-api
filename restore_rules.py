import os

file_path = 'src/contexts/data_quality_triage/domain/educa/rules/domain/family_rules.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

rules_to_add = '''
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
        
        ben_name = domain_entity.beneficiary.full_name or ""
        
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
                
                # Check with exact substring match for simplicity and safety
                found_match = any(last_name in adult_norm for last_name in ben_last_names)
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
'''

if 'class UniqueParentRoleRule' not in content:
    content += rules_to_add
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
