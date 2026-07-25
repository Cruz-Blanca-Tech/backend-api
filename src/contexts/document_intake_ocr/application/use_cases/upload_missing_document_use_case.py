import logging
from uuid import UUID
from typing import Dict, Any

from src.contexts.document_intake_ocr.domain.repositories.batch_repository import BatchRepository
from src.contexts.document_intake_ocr.domain.repositories.activity_repository import ActivityRepository
from src.contexts.document_intake_ocr.application.services.single_document_processor import SingleDocumentProcessor
from src.contexts.document_intake_ocr.application.event_publishers.dossier_event_publisher import DossierEventPublisher
from src.contexts.document_intake_ocr.domain.entities.document import DocumentItem
from src.contexts.document_intake_ocr.domain.services.document_filter_service import DocumentFilterService
from src.contexts.document_intake_ocr.domain.value_objects.raw_file import RawFile
from src.contexts.document_intake_ocr.application.schemas.upload_missing_document_schema import UploadMissingDocumentRequest
from src.core.validators.exceptions import EntityNotFoundException

logger = logging.getLogger(__name__)

class UploadMissingDocumentUseCase:
    def __init__(
        self,
        batch_repo: BatchRepository,
        activity_repo: ActivityRepository,
        single_document_processor: SingleDocumentProcessor,
        event_publisher: DossierEventPublisher
    ):
        self.batch_repo = batch_repo
        self.activity_repo = activity_repo
        self.single_document_processor = single_document_processor
        self.event_publisher = event_publisher

    async def execute(
        self, 
        batch_id: UUID, 
        dni_reference: str, 
        request: UploadMissingDocumentRequest, 
        user_id: UUID,
        user_email: str
    ) -> Dict[str, Any]:
        
        batch = await self.batch_repo.get_by_id(batch_id)
        if not batch:
            raise EntityNotFoundException(f"Lote {batch_id} no encontrado")

        activity = await self.activity_repo.get_by_id(batch.activity_id)
        if not activity:
            raise EntityNotFoundException(f"Actividad {batch.activity_id} no encontrada")

        dossier = next((d for d in batch.dossiers if str(d.dni) == dni_reference), None)
        if not dossier:
            raise EntityNotFoundException(f"Expediente con DNI {dni_reference} no encontrado en el lote {batch_id}")

        # Parse the forged file name to get the code
        raw_file = RawFile(source_id=request.file.source_id, file_name=request.file.file_name)
        extracted_dni = raw_file.extracted_dni
        extracted_code = raw_file.extracted_code
        
        if not extracted_dni or not extracted_code:
            raise ValueError(f"El nombre del archivo {raw_file.file_name} no tiene el formato esperado (DNI_CODIGO.ext).")
            
        document_code = extracted_code.code
            
        config_id = activity.get_config_id_by_code(str(document_code))
        
        # Create DocumentItem
        doc = DocumentItem.create_valid(
            source_id=raw_file.source_id,
            document_code=extracted_code,
            file_name=raw_file.file_name,
            dni_ref=extracted_dni,
            config_id=config_id
        )
        
        dossier.add_document(doc)
        
        # Process the single document synchronously (OCR, Azure)
        # We need the target folder ID from the storage adapter.
        target_folder_id = await self.single_document_processor.storage.ensure_batch_directory(activity.name, str(batch_id))
        
        await self.single_document_processor.execute(
            doc=doc,
            model_id=activity.get_model_id_for_document(str(document_code)),
            target_folder_id=target_folder_id,
            user_email=user_email
        )
        
        # Update Dossier status
        dossier.update_status(activity.required_documents)
        
        # Save batch
        await self.batch_repo.save(batch)
        
        # Dispatch event to trigger Triage Re-evaluation
        # If it didn't fail, we dispatch the created event so Triage can update
        if doc.status.value != "FAILED":
            await self.event_publisher.publish_created(dossier, activity)
            
        return {
            "message": "Documento subido y procesado exitosamente.",
            "document_status": doc.status.value,
            "dossier_status": dossier.status.value
        }
