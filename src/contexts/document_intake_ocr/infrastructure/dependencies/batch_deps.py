# Puedes agregar esto al final de tu archivo dependencies.py actual

import json
import os
from fastapi import Depends
from src.core.database import get_async_db  # Tu generador de sesión de base de datos

# 1. Repositorios (Asumiendo que ya tienes las clases SQL creadas)
from src.contexts.document_intake_ocr.application.use_cases.process_batch.batch_processing_orchestrator import BatchProcessingOrchestrator
from src.contexts.document_intake_ocr.application.use_cases.process_batch.process_batch import ProcessBatchUseCase
from src.contexts.document_intake_ocr.infrastructure.dependencies.activity_deps import get_activity_repository
from src.contexts.document_intake_ocr.infrastructure.persistence.repositories.sql_activity_repository import SqlActivityRepository
from src.contexts.document_intake_ocr.infrastructure.persistence.repositories.sql_batch_repository import SqlBatchRepository

# 2. Adaptadores de Infraestructura Externa
from src.contexts.document_intake_ocr.infrastructure.adapters.google_drive_storage_adapter import GoogleDriveStorageAdapter

# 3. Servicios de Aplicación (Los nuevos que creamos hoy)
from src.contexts.document_intake_ocr.application.services.single_document_processor import SingleDocumentProcessor
from src.contexts.document_intake_ocr.application.services.single_dossier_processor import SingleDossierProcessor
from src.core.config import settings

# 4. Caso de Uso


# ==========================================
# PROVEEDORES DE REPOSITORIOS (BD)
# ==========================================

def get_batch_repository(db = Depends(get_async_db)) -> SqlBatchRepository:
    return SqlBatchRepository(db)

    
# ==========================================
# PROVEEDORES DE ADAPTADORES (NUBE)
# ==========================================
def get_storage_adapter() -> GoogleDriveStorageAdapter:
    # Si settings.google_client_secret es el string JSON, lo parseamos aquí
    if isinstance(settings.GOOGLE_CLIENT_SECRET, str):
        credentials_info = json.loads(settings.GOOGLE_CLIENT_SECRET)
    else:
        credentials_info = settings.GOOGLE_CLIENT_SECRET

    return GoogleDriveStorageAdapter(
        credentials_info=credentials_info,
        scopes=['https://www.googleapis.com/auth/drive'],
        base_folder_id= settings.GOOGLE_DRIVE_TEMPORARY_CUSTODY_ID
    )
def get_extractor_adapter():
    return None 


# ==========================================
# PROVEEDORES DE SERVICIOS DE APLICACIÓN (WORKERS)
# ==========================================
def get_single_document_processor(
    storage: GoogleDriveStorageAdapter = Depends(get_storage_adapter),
    extractor = Depends(get_extractor_adapter)
) -> SingleDocumentProcessor:
    return SingleDocumentProcessor(storage_adapter=storage, extractor_adapter=extractor)

def get_single_dossier_processor(
    doc_processor: SingleDocumentProcessor = Depends(get_single_document_processor)
) -> SingleDossierProcessor:
    return SingleDossierProcessor(single_doc_processor=doc_processor)

def get_batch_orchestrator(
    activity_repo: SqlActivityRepository = Depends(get_activity_repository),
    batch_repo: SqlBatchRepository = Depends(get_batch_repository),
    # Aquí obtenemos el storage que YA viene configurado con el ID
    storage: GoogleDriveStorageAdapter = Depends(get_storage_adapter),
    dossier_processor: SingleDossierProcessor = Depends(get_single_dossier_processor)
) -> BatchProcessingOrchestrator:
    return BatchProcessingOrchestrator(
        activity_repo=activity_repo,
        batch_repo=batch_repo,
        storage_adapter=storage,
        single_dossier_processor=dossier_processor,
        # Importante: El ID ya está en el 'storage' que inyectamos arriba
    )

# ==========================================
# PROVEEDOR DEL CASO DE USO PRINCIPAL
# ==========================================
def get_process_batch_use_case(
    activity_repo: SqlActivityRepository = Depends(get_activity_repository),
    batch_repo: SqlBatchRepository = Depends(get_batch_repository),
    orchestrator: BatchProcessingOrchestrator = Depends(get_batch_orchestrator)
) -> ProcessBatchUseCase:
    """
    Este es el único método que llamarás desde tu Router (Endpoint).
    FastAPI se encargará de ejecutar todo el árbol hacia arriba automáticamente.
    """
    return ProcessBatchUseCase(
        activity_repo=activity_repo,
        batch_repo=batch_repo,
        batch_orchestrator=orchestrator
    )