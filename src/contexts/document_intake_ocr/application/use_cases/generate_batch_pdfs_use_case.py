import io
import logging
from uuid import UUID
from datetime import datetime
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from collections import defaultdict

from src.contexts.core_beneficiary_management.domain.events.beneficiary_events import DossierPdfArchivedEvent
from src.contexts.document_intake_ocr.domain.ports.document_storage import DocumentStorage
from src.contexts.document_intake_ocr.infrastructure.persistence.model.document_item_model import DocumentItemModel
from src.core.events.event_dispatcher import EventDispatcher

logger = logging.getLogger(__name__)

class GenerateBatchPdfsUseCase:
    def __init__(self, storage: DocumentStorage, session: AsyncSession):
        self.storage = storage
        self.session = session

    async def execute(self, batch_id: UUID):
        logger.info(f"Generating PDFs for all dossiers in batch {batch_id}")
        
        # 1. Fetch all document records for this batch
        stmt = select(DocumentItemModel).where(
            DocumentItemModel.batch_id == batch_id
        )
        result = await self.session.execute(stmt)
        documents = result.scalars().all()
        
        if not documents:
            logger.warning(f"No documents found for batch {batch_id}")
            return

        # 2. Group documents by DNI reference
        docs_by_dni = defaultdict(list)
        for doc in documents:
            if doc.dni_reference:
                docs_by_dni[doc.dni_reference].append(doc)

        for dni, docs in docs_by_dni.items():
            logger.info(f"Processing PDF generation for DNI: {dni}")
            images = []
            for doc in docs:
                if not doc.custody_id:
                    continue
                try:
                    img_bytes = self.storage.download_file_to_memory(doc.custody_id)
                    img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
                    images.append(img)
                except Exception as e:
                    logger.error(f"Error processing doc {doc.id} with custody_id {doc.custody_id} for DNI {dni}: {e}")
            
            if not images:
                logger.warning(f"No valid images downloaded for DNI {dni}")
                continue

            try:
                # Create PDF in memory
                pdf_buffer = io.BytesIO()
                images[0].save(
                    pdf_buffer,
                    "PDF",
                    resolution=100.0,
                    save_all=True,
                    append_images=images[1:]
                )
                pdf_bytes = pdf_buffer.getvalue()

                # Create folder for Beneficiary in Drive
                folder_id = self.storage.ensure_beneficiary_directory(dni)

                # Upload PDF
                year = datetime.utcnow().year
                filename = f"Dossier_Inscripcion_{dni}_{year}.pdf"
                file_url = self.storage.upload_file_to_folder(folder_id, pdf_bytes, filename, mime_type="application/pdf")

                # Emit event
                await EventDispatcher.dispatch(DossierPdfArchivedEvent(
                    beneficiary_dni=dni,
                    triage_case_id=None,  # Not needed for MDM association
                    pdf_url=file_url,
                    year=year
                ))
                logger.info(f"Successfully generated and uploaded PDF for {dni}: {file_url}")
            except Exception as e:
                logger.error(f"Failed to generate/upload PDF for DNI {dni}: {e}")
