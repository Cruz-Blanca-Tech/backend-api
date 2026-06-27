import os
import re

def replace_in_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    original_content = content
    
    # Domain replacements
    content = re.sub(r'from src\.contexts\.data_quality_triage\.domain\.dtos', r'from src.contexts.data_quality_triage.domain.shared.dtos', content)
    content = re.sub(r'from src\.contexts\.data_quality_triage\.domain\.entities', r'from src.contexts.data_quality_triage.domain.shared.entities', content)
    content = re.sub(r'from src\.contexts\.data_quality_triage\.domain\.events', r'from src.contexts.data_quality_triage.domain.shared.events', content)
    content = re.sub(r'from src\.contexts\.data_quality_triage\.domain\.ports', r'from src.contexts.data_quality_triage.domain.shared.ports', content)
    content = re.sub(r'from src\.contexts\.data_quality_triage\.domain\.repositories', r'from src.contexts.data_quality_triage.domain.shared.repositories', content)
    content = re.sub(r'from src\.contexts\.data_quality_triage\.domain\.strategies', r'from src.contexts.data_quality_triage.domain.shared.strategies', content)
    content = re.sub(r'from src\.contexts\.data_quality_triage\.domain\.utils', r'from src.contexts.data_quality_triage.domain.shared.utils', content)
    
    # Application replacements
    content = re.sub(r'from src\.contexts\.data_quality_triage\.application\.dtos', r'from src.contexts.data_quality_triage.application.shared.dtos', content)
    content = re.sub(r'from src\.contexts\.data_quality_triage\.application\.factories', r'from src.contexts.data_quality_triage.application.shared.factories', content)
    content = re.sub(r'from src\.contexts\.data_quality_triage\.application\.handlers', r'from src.contexts.data_quality_triage.application.shared.handlers', content)
    content = re.sub(r'from src\.contexts\.data_quality_triage\.application\.mappers', r'from src.contexts.data_quality_triage.application.shared.mappers', content)
    content = re.sub(r'from src\.contexts\.data_quality_triage\.application\.normalizers', r'from src.contexts.data_quality_triage.application.shared.normalizers', content)
    content = re.sub(r'from src\.contexts\.data_quality_triage\.application\.services', r'from src.contexts.data_quality_triage.application.shared.services', content)
    content = re.sub(r'from src\.contexts\.data_quality_triage\.application\.use_cases', r'from src.contexts.data_quality_triage.application.shared.use_cases', content)

    if content != original_content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Updated imports in {filepath}")

def main():
    root_dir = "src/contexts/data_quality_triage"
    for subdir, dirs, files in os.walk(root_dir):
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(subdir, file)
                replace_in_file(filepath)
                
    # Also fix imports in the main app router if it exists outside the BC
    main_router = "src/presentation/api/main.py"
    if os.path.exists(main_router):
        replace_in_file(main_router)

if __name__ == "__main__":
    main()
