import re

with open('src/contexts/data_quality_triage/domain/educa/rules/domain/family_rules.py', 'r', encoding='utf-8') as f:
    content = f.read()

translator_func = '''
def _translate_role(role) -> str:
    if not role: return "Familiar"
    r = str(role).upper()
    if r == "FATHER": return "Padre"
    if r == "MOTHER": return "Madre"
    if r == "SIBLING": return "Hermano(a)"
    if r == "GRANDPARENT": return "Abuelo(a)"
    return "Familiar"

class GuardianPresenceRule'''

content = content.replace('class GuardianPresenceRule', translator_func)
content = content.replace('adult.relationship', '_translate_role(adult.relationship)')
content = content.replace('prev_adult.relationship', '_translate_role(prev_adult.relationship)')
content = content.replace('_translate_role(_translate_role(', '_translate_role(') # just in case

with open('src/contexts/data_quality_triage/domain/educa/rules/domain/family_rules.py', 'w', encoding='utf-8') as f:
    f.write(content)
