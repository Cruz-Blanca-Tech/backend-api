import os
import re

def refactor_use_cases():
    root = r"c:\Users\rimbo\Desktop\cruz blanca\backend-api\src\contexts\data_quality_triage\application\shared\use_cases"
    files_to_fix = [
        "approve_triage_case_use_case.py",
        "reject_triage_case_use_case.py",
        "revalidate_triage_case_use_case.py",
        "update_dossier_use_case.py",
        "create_dossier_use_case.py"
    ]
    
    old_import = r"from src\.contexts\.data_quality_triage\.infrastructure\.persistence\.repositories\.sql_triage_case_repository import SqlTriageCaseRepository"
    new_import = "from src.contexts.data_quality_triage.domain.shared.repositories.triage_repository import TriageRepository"
    
    for filename in files_to_fix:
        filepath = os.path.join(root, filename)
        if not os.path.exists(filepath):
            continue
            
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            
        content = re.sub(old_import, new_import, content)
        content = content.replace("SqlTriageCaseRepository", "TriageRepository")
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
            
        print(f"Refactored: {filename}")

if __name__ == "__main__":
    refactor_use_cases()
