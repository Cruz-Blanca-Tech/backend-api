import re

deps_file = 'c:/Users/enzot/Documents/code/CruzBlanca/backend-api/src/contexts/document_intake_ocr/infrastructure/dependencies/batch_deps.py'
with open(deps_file, 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('SqlActivityRepository', 'ActivityRepository')
content = content.replace('SqlBatchRepository', 'BatchRepository')
content = content.replace('GoogleDriveStorageAdapter', 'DocumentStorage')

with open(deps_file, 'w', encoding='utf-8') as f:
    f.write(content)
