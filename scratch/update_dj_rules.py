import re

# 1. Update family_rules.py
file_path = 'src/contexts/data_quality_triage/domain/educa/rules/domain/family_rules.py'
with open(file_path, 'r', encoding='utf-8') as f:
    family_rules = f.read()

new_rule = """
class DjSignerPresenceRule(DomainRule):
    \"\"\"
    Verifica que la Declaración Jurada (DJ) tenga un firmante extraído.
    \"\"\"
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

"""

if "DjSignerPresenceRule" not in family_rules:
    family_rules += new_rule
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(family_rules)


# 2. Update educa_inscription_dossier.py
dossier_path = 'src/contexts/data_quality_triage/domain/educa/value_objects/educa_inscription_dossier.py'
with open(dossier_path, 'r', encoding='utf-8') as f:
    dossier = f.read()

if "DjSignerPresenceRule" not in dossier:
    # Add to imports
    dossier = dossier.replace("DjFinsSignerCoherenceRule", "DjFinsSignerCoherenceRule, DjSignerPresenceRule")
    # Add to rules array
    dossier = dossier.replace("DjFinsSignerCoherenceRule(),", "DjFinsSignerCoherenceRule(),\n            DjSignerPresenceRule(),")
    
    with open(dossier_path, 'w', encoding='utf-8') as f:
        f.write(dossier)

print("Reglas actualizadas.")
