with open('src/contexts/data_quality_triage/domain/educa/rules/domain/family_rules.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

start = -1
for i, line in enumerate(lines):
    if "class EmergencyContactRule" in line:
        start = i
        break

if start != -1:
    end = start + 40
    print("".join(lines[start:end]))
