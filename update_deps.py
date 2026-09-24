import re

deps_file = 'src/contexts/document_intake_ocr/infrastructure/dependencies/batch_deps.py'
with open(deps_file, 'r', encoding='utf-8') as f:
    deps_content = f.read()

import_statement = "from src.contexts.document_intake_ocr.application.use_cases.reprocess_dossier_use_case import ReprocessDossierUseCase\n"
if "ReprocessDossierUseCase" not in deps_content:
    deps_content = import_statement + deps_content

func = '''
def get_reprocess_dossier_use_case(
    activity_repo: SqlActivityRepository = Depends(get_activity_repository),
    batch_repo: SqlBatchRepository = Depends(get_batch_repository),
    storage: GoogleDriveStorageAdapter = Depends(get_storage_adapter),
    doc_processor: SingleDocumentProcessor = Depends(get_single_document_processor),
    event_publisher: DossierEventPublisher = Depends(get_dossier_event_publisher),
):
    return ReprocessDossierUseCase(
        activity_repo=activity_repo,
        batch_repo=batch_repo,
        storage_adapter=storage,
        single_doc_processor=doc_processor,
        event_publisher=event_publisher,
    )
'''
if "get_reprocess_dossier_use_case" not in deps_content:
    deps_content += func

with open(deps_file, 'w', encoding='utf-8') as f:
    f.write(deps_content)
