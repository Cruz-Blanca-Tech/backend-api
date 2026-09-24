import re

usecase_file = 'src/contexts/document_intake_ocr/application/use_cases/reprocess_dossier_use_case.py'
with open(usecase_file, 'r', encoding='utf-8') as f:
    u_content = f.read()

# Change from background task to synchronous await
u_content = u_content.replace(
    'background_tasks.add_task(\n            self._process_in_background,\n            batch_id,\n            dni_reference,\n            user_email\n        )',
    'await self._process_in_background(batch_id, dni_reference, user_email)'
)

with open(usecase_file, 'w', encoding='utf-8') as f:
    f.write(u_content)
