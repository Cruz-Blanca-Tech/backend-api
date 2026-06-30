# src/contexts/document_intake_ocr/application/services/batch_processing_orchestrator.py

import logging
from uuid import UUID

from src.contexts.document_intake_ocr.domain.repositories.activity_repository import ActivityRepository
from src.contexts.document_intake_ocr.domain.repositories.batch_repository import BatchRepository
from src.contexts.document_intake_ocr.domain.ports.document_storage import DocumentStorage
from src.contexts.document_intake_ocr.application.services.single_dossier_processor import SingleDossierProcessor
from src.core.validators.exceptions import ExternalServiceException
from src.contexts.document_intake_ocr.application.event_publishers.dossier_event_publisher import DossierEventPublisher

logger = logging.getLogger(__name__)

class BatchProcessingOrchestrator:
    def __init__(
        self, 
        activity_repo: ActivityRepository, 
        batch_repo: BatchRepository,
        storage_adapter: DocumentStorage,
        single_dossier_processor: SingleDossierProcessor,
        event_publisher: DossierEventPublisher,
    ):
        self.activity_repo = activity_repo
        self.batch_repo = batch_repo
        self.storage_adapter = storage_adapter
        self.single_dossier_processor = single_dossier_processor
        self.event_publisher = event_publisher

    async def run_pipeline(self, batch_id: UUID, user_email: str) -> None:
        logger.info(f"[BATCH START] Iniciando pipeline asíncrono para Lote: {batch_id}")
        
        batch = await self.batch_repo.get_by_id(batch_id)
        logger.info(f"DEBUG: Batch cargado: {batch.id}")
        if not batch: return

        activity = await self.activity_repo.get_by_id(batch.activity_id)
        
        try:
            # 1. Preparar Bóveda
            batch_target_folder_id = await self.storage_adapter.ensure_batch_directory(
                activity_name=activity.name,
                batch_id=str(batch.id)
            )
            
            print(f"DEBUG: Fábrica construyó batch con {len(batch.dossiers)} expedientes")
            # 2. PROCESAMIENTO A NIVEL EXPEDIENTE (Adiós doble bucle anidado)
            total_procesados = 0
            for dossier in batch.dossiers:
                procesados_en_dossier = await self.single_dossier_processor.execute(
                    dossier=dossier,
                    activity=activity, # <--- Súper limpio 
                    target_folder_id=batch_target_folder_id, 
                    user_email=user_email
                )
                print(f"DEBUG: Expediente {dossier.dni} tiene {len(dossier.documents)} documentos.")
                total_procesados += procesados_en_dossier   
            
            # 3. Validar si todo falló
            all_docs = batch.get_all_documents()
            failed_docs_count = sum(1 for d in all_docs if d.status.value == "FAILED")
            
            if len(all_docs) > 0 and failed_docs_count == len(all_docs):
                batch.mark_as_failed(reason="Todos los documentos del lote fallaron durante el procesamiento.")
                logger.warning(f"[BATCH FAILED] Lote {batch_id} marcado como FAILED porque el 100% de sus archivos fallaron.")
            else:
                batch.mark_as_pending()
                logger.info(f"[BATCH COMPLETE] Lote {batch_id} finalizado y marcado como PENDING. Archivos: {total_procesados}")
                
            await self.batch_repo.save(batch)
            
            # 4. Detonar los eventos de Triaje AHORA que los datos OCR están guardados en la BD
            for dossier in batch.dossiers:
                # Solo disparamos eventos para los expedientes que tengan al menos 1 documento extraído exitosamente
                if any(doc.status.value != "FAILED" for doc in dossier.documents):
                    await self.event_publisher.publish_created(dossier, activity)


        except ExternalServiceException as ext_error:
            logger.critical(f"[BATCH CRITICAL] Fallo en la infraestructura base: {ext_error.message}")
            batch.mark_as_failed(reason=f"Fallo de infraestructura en Bóveda: {ext_error.message}")
            await self.batch_repo.save(batch)
        except Exception as e:
            logger.critical(f"[BATCH CRITICAL] Error fatal inesperado: {str(e)}")