import logging
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.events.event_dispatcher import EventDispatcher
from src.contexts.shared.events.dossier_approved_event import DossierApprovedEvent
from src.contexts.document_intake_ocr.application.use_cases.generate_dossier_pdf_use_case import GenerateDossierPdfUseCase
from src.contexts.document_intake_ocr.infrastructure.adapters.google_drive_storage_adapter import GoogleDriveStorageAdapter
from src.core.config.settings import settings

logger = logging.getLogger(__name__)

async def handle_dossier_approved_for_pdf(event: DossierApprovedEvent, session: AsyncSession) -> None:
    logger.info(f"OCR Context handling DossierApprovedEvent to generate PDF for case: {event.triage_case_id}")
    try:
        storage = GoogleDriveStorageAdapter(
            credentials_info=settings.GOOGLE_CREDENTIALS,
            scopes=['https://www.googleapis.com/auth/drive'],
            base_folder_id=settings.GOOGLE_DRIVE_CONSOLIDATED_DOSSIERS_ID
        )
        uc = GenerateDossierPdfUseCase(storage, session)
        await uc.execute(event)
        logger.info(f"Successfully generated PDF for DNI: {event.dni_reference}")
    except Exception as e:
        logger.error(f"Failed to generate PDF for case {event.triage_case_id}: {str(e)}")

def register_ocr_event_handlers():
    EventDispatcher.register(DossierApprovedEvent, handle_dossier_approved_for_pdf)
