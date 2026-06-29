import logging
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.events.event_dispatcher import EventDispatcher
from src.contexts.shared.events.dossier_approved_event import DossierApprovedEvent
from src.contexts.core_beneficiary_management.domain.events.beneficiary_events import DossierPdfArchivedEvent
from src.contexts.core_beneficiary_management.application.use_cases.process_approved_triage_case_use_case import ProcessApprovedTriageCaseUseCase
from src.contexts.core_beneficiary_management.infrastructure.persistence.repositories.sql_beneficiary_repository import SqlBeneficiaryRepository
from src.contexts.core_beneficiary_management.infrastructure.persistence.model.beneficiary_models import HistoricalDocumentModel
from src.core.database import async_session_maker
import uuid

logger = logging.getLogger(__name__)

async def handle_dossier_approved_event(event: DossierApprovedEvent) -> None:
    logger.info(f"Beneficiary Core handling DossierApprovedEvent for case: {event.triage_case_id}")
    try:
        async with async_session_maker() as session:
            repo = SqlBeneficiaryRepository(session)
            uc = ProcessApprovedTriageCaseUseCase(repo)
            await uc.execute(event)
            await session.commit()
        logger.info(f"Successfully processed DossierApprovedEvent for DNI: {event.dni_reference}")
    except Exception as e:
        logger.error(f"Failed to process DossierApprovedEvent for case {event.triage_case_id}: {str(e)}")

def register_beneficiary_event_handlers():
    EventDispatcher.register(DossierApprovedEvent, handle_dossier_approved_event)
    EventDispatcher.register(DossierPdfArchivedEvent, handle_dossier_pdf_archived_event)

async def handle_dossier_pdf_archived_event(event: DossierPdfArchivedEvent) -> None:
    logger.info(f"Beneficiary Core handling DossierPdfArchivedEvent for DNI: {event.beneficiary_dni}")
    try:
        async with async_session_maker() as session:
            repo = SqlBeneficiaryRepository(session)
            beneficiary = await repo.get_by_dni(event.beneficiary_dni)
            if beneficiary:
                doc = HistoricalDocumentModel(
                    id=uuid.uuid4(),
                    document_type="INSCRIPTION_DOSSIER",
                    year=event.year,
                    file_url=event.pdf_url
                )
                beneficiary.historical_documents.append(doc)
                await repo.save(beneficiary)
                await session.commit()
                logger.info(f"Successfully saved historical PDF link for DNI: {event.beneficiary_dni}")
            else:
                logger.warning(f"Could not find beneficiary with DNI {event.beneficiary_dni} to attach PDF")
    except Exception as e:
        logger.error(f"Failed to save historical PDF for DNI {event.beneficiary_dni}: {str(e)}")
