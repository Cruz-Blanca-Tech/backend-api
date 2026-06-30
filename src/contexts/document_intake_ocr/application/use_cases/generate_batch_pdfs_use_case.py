import io
import logging
from typing import Dict, List
from uuid import UUID
from datetime import datetime
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from src.contexts.core_beneficiary_management.domain.events.beneficiary_events import DossierPdfArchivedEvent
from src.contexts.document_intake_ocr.domain.ports.document_storage import DocumentStorage
from src.contexts.document_intake_ocr.infrastructure.persistence.model.document_item_model import DocumentItemModel
from src.core.events.event_dispatcher import EventDispatcher

logger = logging.getLogger(__name__)

class GenerateBatchPdfsUseCase:
    def __init__(self, storage: DocumentStorage, session: AsyncSession):
        self.storage = storage
        self.session = session

    async def execute(self, batch_id: UUID, approved_dossiers: Dict[str, List[UUID]]):
        """
        approved_dossiers: { dni_reference -> [doc_id, doc_id, ...] }
        These come directly from the TriageCase.document_ids so they are always in sync.
        """
        if not approved_dossiers:
            logger.warning(f"No approved dossiers to generate PDFs for batch {batch_id}")
            return

        logger.info(f"Generating PDFs for {len(approved_dossiers)} approved dossiers in batch {batch_id}")

        for dni, doc_ids in approved_dossiers.items():
            logger.info(f"Processing PDF generation for DNI: {dni} ({len(doc_ids)} documents)")

            # Fetch the concrete document records by their exact IDs
            stmt = select(DocumentItemModel).where(
                DocumentItemModel.id.in_(doc_ids)
            )
            result = await self.session.execute(stmt)
            docs = result.scalars().all()

            if not docs:
                logger.warning(f"No document records found for DNI {dni} in batch {batch_id}")
                continue

            images = []
            for doc in docs:
                if not doc.custody_id:
                    logger.warning(f"Document {doc.id} has no custody_id, skipping")
                    continue
                try:
                    img_bytes = self.storage.download_file_to_memory(doc.custody_id)
                    img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
                    images.append(img)
                except Exception as e:
                    logger.error(f"Error downloading doc {doc.id} (custody_id={doc.custody_id}) for DNI {dni}: {e}")

            if not images:
                logger.warning(f"No valid images downloaded for DNI {dni}")
                continue

            try:
                # Build PDF in memory
                pdf_buffer = io.BytesIO()
                images[0].save(
                    pdf_buffer, "PDF", resolution=100.0,
                    save_all=True, append_images=images[1:]
                )
                pdf_bytes = pdf_buffer.getvalue()

                # Ensure Drive folder for this dossier
                folder_id = await self.storage.ensure_beneficiary_directory(dni)

                # Upload PDF
                year = datetime.utcnow().year
                filename = f"Dossier_Inscripcion_{dni}_{year}.pdf"
                file_url = await self.storage.upload_file_to_folder(
                    folder_id, pdf_bytes, filename, mime_type="application/pdf"
                )

                # Notify MDM with the archived PDF URL
                await EventDispatcher.dispatch(DossierPdfArchivedEvent(
                    beneficiary_dni=dni,
                    triage_case_id=None,
                    pdf_url=file_url,
                    year=year
                ))
                logger.info(f"PDF generated and uploaded for DNI {dni}: {file_url}")
            except Exception as e:
                logger.error(f"Failed to generate/upload PDF for DNI {dni}: {e}")
