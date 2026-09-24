import logging
from uuid import UUID
from fastapi import BackgroundTasks
from src.contexts.document_intake_ocr.domain.repositories.batch_repository import BatchRepository
from src.contexts.document_intake_ocr.domain.repositories.activity_repository import ActivityRepository
from src.contexts.document_intake_ocr.domain.ports.document_storage import DocumentStorage
from src.contexts.document_intake_ocr.domain.entities.document import DocumentStatus
from src.contexts.document_intake_ocr.domain.entities.dossier import Dossier
from src.contexts.document_intake_ocr.domain.value_objects.dni import DNI
from src.contexts.document_intake_ocr.application.services.single_document_processor import SingleDocumentProcessor
from src.contexts.document_intake_ocr.application.event_publishers.dossier_event_publisher import DossierEventPublisher
from src.core.validators.exceptions import EntityNotFoundException

logger = logging.getLogger(__name__)

class ReprocessDossierUseCase:
    def __init__(
        self,
        batch_repo: BatchRepository,
        activity_repo: ActivityRepository,
        storage_adapter: DocumentStorage,
        single_doc_processor: SingleDocumentProcessor,
        event_publisher: DossierEventPublisher,
    ):
        self.batch_repo = batch_repo
        self.activity_repo = activity_repo
        self.storage_adapter = storage_adapter
        self.single_doc_processor = single_doc_processor
        self.event_publisher = event_publisher

    async def execute(
        self,
        batch_id: UUID,
        dni_reference: str,
        user_email: str,
        background_tasks: BackgroundTasks,
    ) -> dict:
        batch = await self.batch_repo.get_by_id(batch_id)
        if not batch:
            raise EntityNotFoundException(f"Lote {batch_id} no encontrado.")

        activity = await self.activity_repo.get_by_id(batch.activity_id)
        if not activity:
            raise EntityNotFoundException(f"Actividad {batch.activity_id} no encontrada.")

        target_dossier = next((d for d in batch.dossiers if str(d.dni) == dni_reference), None)
        rejected_matches = [doc for doc in batch.rejected_documents if str(doc.dni_reference) == dni_reference]

        if not target_dossier and not rejected_matches:
            raise EntityNotFoundException(f"Expediente con DNI {dni_reference} no encontrado.")

        # Re-create dossier if all docs were failed
        if not target_dossier:
            target_dossier = Dossier(dni=DNI(dni_reference), activity_id=activity.id, batch_id=batch.id)
            batch.add_dossier(target_dossier)

        # Move rejected docs back to the dossier
        for doc in rejected_matches:
            if doc in batch._rejected_documents:
                batch._rejected_documents.remove(doc)
            target_dossier.add_document(doc)

        # Reset status for all documents to PROCESSING / PENDING
        for doc in target_dossier.documents:
            doc.status = DocumentStatus.PENDING
            doc.extracted_data = {}
            doc.failure_reason = None
        
        target_dossier.update_status(activity.required_documents)
        await self.batch_repo.save(batch)

        # Reprocesamiento síncrono para que la UI se quede cargando
        target_folder_id = await self.storage_adapter.ensure_batch_directory(activity.name, str(batch.id))
        
        for doc in target_dossier.documents:
            if doc.status == DocumentStatus.PENDING:
                try:
                    model_id = activity.get_model_id_for_document(str(doc.document_code))
                    await self.single_doc_processor.execute(
                        doc=doc,
                        model_id=model_id,
                        target_folder_id=target_folder_id,
                        user_email=user_email,
                    )
                except Exception as doc_err:
                    logger.error(f"[REPROCESS] Error procesando doc {doc.file_name}: {doc_err}")
                    doc.mark_as_failed(reason=str(doc_err))

        target_dossier.update_status(activity.required_documents)
        
        if batch.status.value == "FAILED":
            all_docs = batch.get_all_documents()
            if any(d.status.value != "FAILED" for d in all_docs):
                batch.mark_as_completed()

        await self.batch_repo.save(batch)

        if any(doc.status.value != "FAILED" for doc in target_dossier.documents):
            await self.event_publisher.publish_created(target_dossier, activity)
            # await self.event_publisher.publish_batch_ocr_completed(batch.id) # Desactivado para evitar auto-cierre

        return {"message": f"Expediente reprocesado y enviado a Triage con éxito."}

    async def _process_in_background(self, batch_id: UUID, dni_reference: str, user_email: str):
        # We need a fresh session for the background task to avoid DetachedInstanceErrors
        from src.core.database import async_session_maker
        from src.contexts.document_intake_ocr.infrastructure.persistence.repositories.sql_batch_repository import SqlBatchRepository
        from src.contexts.document_intake_ocr.infrastructure.persistence.repositories.sql_activity_repository import SqlActivityRepository
        
        async with async_session_maker() as session:
            bg_batch_repo = SqlBatchRepository(session)
            bg_activity_repo = SqlActivityRepository(session)
            
            logger.info(f"[REPROCESS] Iniciando reprocesamiento ASÍNCRONO del expediente {dni_reference}")
            try:
                batch = await bg_batch_repo.get_by_id(batch_id)
                activity = await bg_activity_repo.get_by_id(batch.activity_id)
                target_dossier = next((d for d in batch.dossiers if str(d.dni) == dni_reference), None)
                
                if not target_dossier:
                    return

                target_folder_id = await self.storage_adapter.ensure_batch_directory(activity.name, str(batch.id))
                
                for doc in target_dossier.documents:
                    if doc.status == DocumentStatus.PENDING:
                        try:
                            model_id = activity.get_model_id_for_document(str(doc.document_code))
                            await self.single_doc_processor.execute(
                                doc=doc,
                                model_id=model_id,
                                target_folder_id=target_folder_id,
                                user_email=user_email,
                            )
                        except Exception as doc_err:
                            logger.error(f"[REPROCESS] Error procesando doc {doc.file_name}: {doc_err}")
                            doc.mark_as_failed(reason=str(doc_err))

                target_dossier.update_status(activity.required_documents)
                
                if batch.status.value == "FAILED":
                    all_docs = batch.get_all_documents()
                    if any(d.status.value != "FAILED" for d in all_docs):
                        batch.mark_as_completed()

                await bg_batch_repo.save(batch)

                # Publish events if at least one doc succeeded.
                # This explicitly invokes the ProcessDossierUseCase of Triage!
                if any(doc.status.value != "FAILED" for doc in target_dossier.documents):
                    await self.event_publisher.publish_created(target_dossier, activity)
                    await self.event_publisher.publish_batch_ocr_completed(batch.id)
                    
                logger.info(f"[REPROCESS] Expediente {dni_reference} completado y enviado a Triage.")
            except Exception as e:
                logger.critical(f"[REPROCESS CRITICAL] {str(e)}")
