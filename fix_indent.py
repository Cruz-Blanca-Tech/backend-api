import sys

with open('src/contexts/data_quality_triage/domain/educa/rules/domain/family_rules.py', 'r', encoding='utf-8') as f:
    c = f.read()

c = c.replace('                contact_adult =', '        contact_adult =')
with open('src/contexts/data_quality_triage/domain/educa/rules/domain/family_rules.py', 'w', encoding='utf-8') as f:
    f.write(c)
