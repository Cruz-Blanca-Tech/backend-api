import re

with open('src/contexts/data_quality_triage/domain/educa/rules/domain/family_rules.py', 'r', encoding='utf-8') as f:
    content = f.read()

translator_code = '''
def _t(role) -> str:
    if not role: return "Familiar"
    r = str(role).upper()
    if r == "FATHER": return "Padre"
    if r == "MOTHER": return "Madre"
    if r == "SIBLING": return "Hermano(a)"
    if r == "GRANDPARENT": return "Abuelo(a)"
    return "Familiar"

class GuardianPresenceRule'''

# Add translation function
content = content.replace('class GuardianPresenceRule', translator_code)

# Replace 'adult.relationship' with '_t(adult.relationship)' ONLY when it's formatted into strings
content = content.replace('adult.relationship or "un familiar"', '_t(adult.relationship) or "un familiar"')
content = content.replace('adult.relationship or "otro familiar"', '_t(adult.relationship) or "otro familiar"')
content = content.replace('prev_adult.relationship or "un familiar"', '_t(prev_adult.relationship) or "un familiar"')
content = content.replace('({adult.relationship})', '({_t(adult.relationship)})')

# Re-add DjFinsSignerCoherenceRule
new_rule = '''
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
'''

if 'class DjFinsSignerCoherenceRule' not in content:
    content += new_rule

with open('src/contexts/data_quality_triage/domain/educa/rules/domain/family_rules.py', 'w', encoding='utf-8') as f:
    f.write(content)
