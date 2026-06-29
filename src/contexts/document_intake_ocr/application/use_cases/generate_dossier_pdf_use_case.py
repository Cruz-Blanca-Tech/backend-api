import io
import logging
from uuid import UUID
from datetime import datetime
from PIL import Image

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from src.contexts.shared.events.dossier_approved_event import DossierApprovedEvent
from src.contexts.core_beneficiary_management.domain.events.beneficiary_events import DossierPdfArchivedEvent
from src.contexts.document_intake_ocr.domain.ports.document_storage import DocumentStorage
from src.contexts.document_intake_ocr.infrastructure.persistence.model.document_item_model import DocumentItemModel
from src.core.events.event_dispatcher import EventDispatcher

logger = logging.getLogger(__name__)

class GenerateDossierPdfUseCase:
    def __init__(self, storage: DocumentStorage, session: AsyncSession):
        self.storage = storage
        self.session = session

    async def execute(self, event: DossierApprovedEvent):
        logger.info(f"Generating PDF for DNI {event.dni_reference}")
        
        # 1. Fetch document records using batch_id and dni_reference
        stmt = select(DocumentItemModel).where(
            DocumentItemModel.batch_id == event.batch_id,
            DocumentItemModel.dni_reference == event.dni_reference
        )
        result = await self.session.execute(stmt)
        documents = result.scalars().all()
        
        if not documents:
            logger.warning(f"No documents found for case {event.triage_case_id}")
            return

        # 2. Download all images
        images = []
        for doc in documents:
            if not doc.custody_id:
                continue
            try:
                # Downloader
                img_bytes = self.storage.download_file_to_memory(doc.custody_id)
                img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
                images.append(img)
            except Exception as e:
                logger.error(f"Error processing doc {doc.id} with custody_id {doc.custody_id}: {e}")
                
        if not images:
            logger.warning(f"No valid images downloaded for case {event.triage_case_id}")
            return
            
        # 3. Create PDF in memory
        pdf_buffer = io.BytesIO()
        images[0].save(
            pdf_buffer,
            "PDF",
            resolution=100.0,
            save_all=True,
            append_images=images[1:]
        )
        pdf_bytes = pdf_buffer.getvalue()
        
        # 4. Create folder for Beneficiary in Custody Drive
        folder_id = self.storage.ensure_beneficiary_directory(event.dni_reference)
        
        # 5. Upload PDF
        year = datetime.utcnow().year
        filename = f"Dossier_Inscripcion_{event.dni_reference}_{year}.pdf"
        file_url = self.storage.upload_file_to_folder(folder_id, pdf_bytes, filename, mime_type="application/pdf")
        
        # 6. Emit Event
        await EventDispatcher.dispatch(DossierPdfArchivedEvent(
            beneficiary_dni=event.dni_reference,
            triage_case_id=event.triage_case_id,
            pdf_url=file_url,
            year=year
        ))
        
        logger.info(f"Successfully generated and uploaded PDF for {event.dni_reference}: {file_url}")
