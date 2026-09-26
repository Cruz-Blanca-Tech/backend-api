import re

file_path = 'src/contexts/data_quality_triage/domain/educa/rules/domain/family_rules.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Reemplazar domain_entity.beneficiary.full_name por la concatenación de first_name y last_name
old_line = 'ben_name = domain_entity.beneficiary.full_name or ""'
new_line = 'ben_name = f"{domain_entity.beneficiary.first_name or \'\'} {domain_entity.beneficiary.last_name or \'\'}".strip()'

if old_line in content:
    content = content.replace(old_line, new_line)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("Corregido exitosamente.")
else:
    print("No se encontró la línea original.")
