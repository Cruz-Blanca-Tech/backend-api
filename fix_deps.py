import re

deps_file = 'src/contexts/document_intake_ocr/infrastructure/dependencies/batch_deps.py'
with open(deps_file, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix the import
content = content.replace(
    'from src.contexts.document_intake_ocr.infrastructure.persistence.repositories.sql_batch_repository import BatchRepository',
    'from src.contexts.document_intake_ocr.infrastructure.persistence.repositories.sql_batch_repository import SqlBatchRepository\nfrom src.contexts.document_intake_ocr.domain.repositories.batch_repository import BatchRepository'
)
content = content.replace(
    'from src.contexts.document_intake_ocr.infrastructure.persistence.repositories.sql_activity_repository import ActivityRepository',
    'from src.contexts.document_intake_ocr.infrastructure.persistence.repositories.sql_activity_repository import SqlActivityRepository\nfrom src.contexts.document_intake_ocr.domain.repositories.activity_repository import ActivityRepository'
)

# Fix the instantiation
content = content.replace('return BatchRepository(db)', 'return SqlBatchRepository(session=db)')
content = content.replace('return ActivityRepository(db)', 'return SqlActivityRepository(session=db)')

# Also GoogleDriveStorageAdapter
content = content.replace(
    'from src.contexts.document_intake_ocr.infrastructure.adapters.google_drive_storage_adapter import DocumentStorage',
    'from src.contexts.document_intake_ocr.infrastructure.adapters.google_drive_storage_adapter import GoogleDriveStorageAdapter\nfrom src.contexts.document_intake_ocr.domain.ports.document_storage import DocumentStorage'
)
content = content.replace(
    'return DocumentStorage(\n        credentials_info=credentials_info,',
    'return GoogleDriveStorageAdapter(\n        credentials_info=credentials_info,'
)

with open(deps_file, 'w', encoding='utf-8') as f:
    f.write(content)
