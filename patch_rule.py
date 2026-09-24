import sys

with open('src/contexts/data_quality_triage/domain/educa/rules/domain/family_rules.py', 'r', encoding='utf-8') as f:
    c = f.read()

old_block = '''        adult_dnis = [(a.dni or "").strip() for a in domain_entity.related_adults.adults if a.dni]
        if emergency_dni not in adult_dnis:
            issues.append(FieldDiscrepancy(
                field_name="related_adults.emergency_contact_dni", expected_pattern="DNI de un adulto registrado", actual_value=str(emergency_dni),
                rule_description="El contacto de emergencia resuelto no corresponde a ningn adulto registrado.", 
                severity="ERROR", document_code="DOMINIO"
            ))
            
        return issues'''

old_block_2 = '''        adult_dnis = [(a.dni or "").strip() for a in domain_entity.related_adults.adults if a.dni]
        if emergency_dni not in adult_dnis:
            issues.append(FieldDiscrepancy(
                field_name="related_adults.emergency_contact_dni", expected_pattern="DNI de un adulto registrado", actual_value=str(emergency_dni),
                rule_description="El contacto de emergencia resuelto no corresponde a ningún adulto registrado.", 
                severity="ERROR", document_code="DOMINIO"
            ))
            
        return issues'''

new_block = '''        contact_adult = next((a for a in domain_entity.related_adults.adults if (a.dni or "").strip() == emergency_dni), None)
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
            
        return issues'''

# Since encoding on disk might be messed up, let's just do a string replacement on a clean prefix/suffix search.
import re
match = re.search(r'adult_dnis = \[\(a\.dni or ""\)\.strip\(\) for a in domain_entity\.related_adults\.adults if a\.dni\].*?return issues', c, re.DOTALL)
if match:
    c = c[:match.start()] + new_block + c[match.end():]
    with open('src/contexts/data_quality_triage/domain/educa/rules/domain/family_rules.py', 'w', encoding='utf-8') as f:
        f.write(c)
    print("Replaced!")
else:
    print("Not found!")
