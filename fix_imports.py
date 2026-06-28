import os
import re

# Update map
updates = {
    # Value Objects (Shared)
    r"from src.contexts.data_quality_triage.domain.value_objects.dossier_data": "from src.contexts.data_quality_triage.domain.shared.value_objects.dossier_data",
    r"from src.contexts.data_quality_triage.domain.value_objects.field_mapping": "from src.contexts.data_quality_triage.domain.shared.value_objects.field_mapping",
    r"from src.contexts.data_quality_triage.domain.value_objects.field_discrepancy": "from src.contexts.data_quality_triage.domain.shared.value_objects.field_discrepancy",
    r"from src.contexts.data_quality_triage.domain.value_objects.quality_rule_result": "from src.contexts.data_quality_triage.domain.shared.value_objects.quality_rule_result",
    r"from src.contexts.data_quality_triage.domain.value_objects.validation_result": "from src.contexts.data_quality_triage.domain.shared.value_objects.validation_result",
    
    # Value Objects (Educa)
    r"from src.contexts.data_quality_triage.domain.value_objects.beneficiary_data": "from src.contexts.data_quality_triage.domain.educa.value_objects.beneficiary_data",
    r"from src.contexts.data_quality_triage.domain.value_objects.parents_data": "from src.contexts.data_quality_triage.domain.educa.value_objects.parents_data",
    r"from src.contexts.data_quality_triage.domain.value_objects.parent_detail": "from src.contexts.data_quality_triage.domain.educa.value_objects.parent_detail",
    r"from src.contexts.data_quality_triage.domain.value_objects.education_data": "from src.contexts.data_quality_triage.domain.educa.value_objects.education_data",
    r"from src.contexts.data_quality_triage.domain.value_objects.medical_data": "from src.contexts.data_quality_triage.domain.educa.value_objects.medical_data",
    r"from src.contexts.data_quality_triage.domain.value_objects.educa_inscription": "from src.contexts.data_quality_triage.domain.educa.value_objects.educa_inscription",
    r"from src.contexts.data_quality_triage.domain.value_objects.raw_data": "from src.contexts.data_quality_triage.domain.educa.value_objects.raw_data",

    # Services
    r"from src.contexts.data_quality_triage.domain.services.dossier_policy": "from src.contexts.data_quality_triage.domain.shared.services.dossier_policy",
    r"from src.contexts.data_quality_triage.domain.services.triage_engine": "from src.contexts.data_quality_triage.domain.shared.services.triage_engine",
    r"from src.contexts.data_quality_triage.domain.services.educa_inscription_policy": "from src.contexts.data_quality_triage.domain.educa.services.educa_inscription_policy",

    # Entities (Shared)
    r"from src.contexts.data_quality_triage.domain.entities.triage_case": "from src.contexts.data_quality_triage.domain.shared.entities.triage_case",

    # Mappers
    r"from src.contexts.data_quality_triage.application.mappers.educa": "from src.contexts.data_quality_triage.application.educa.mappers",
    r"from src.contexts.data_quality_triage.application.mappers.educa_inscription_mapper": "from src.contexts.data_quality_triage.application.educa.mappers.educa_inscription_mapper",

    # Schemas
    r"from src.contexts.data_quality_triage.application.schemas.dossier_schemas": "from src.contexts.data_quality_triage.application.educa.schemas.educa_schemas",
    r"from src.contexts.data_quality_triage.application.schemas": "from src.contexts.data_quality_triage.application.shared.schemas",
}

def replace_in_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    original_content = content
    for pattern, replacement in updates.items():
        content = content.replace(pattern, replacement)

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

if __name__ == "__main__":
    main()
