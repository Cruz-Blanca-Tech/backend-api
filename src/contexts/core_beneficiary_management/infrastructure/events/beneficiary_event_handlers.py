import uuid
import logging
from src.core.database import async_session_maker
from src.core.events.event_dispatcher import EventDispatcher
from src.contexts.shared.events.dossier_approved_event import DossierApprovedEvent
from src.contexts.core_beneficiary_management.domain.events.beneficiary_events import DossierPdfArchivedEvent
from src.contexts.core_beneficiary_management.infrastructure.persistence.repositories.sql_beneficiary_repository import SqlBeneficiaryRepository
from src.contexts.core_beneficiary_management.application.use_cases.process_approved_triage_case_use_case import ProcessApprovedTriageCaseUseCase
from src.contexts.core_beneficiary_management.domain.value_objects.historical_document import HistoricalDocument

logger = logging.getLogger(__name__)

async def handle_dossier_approved_event(event: DossierApprovedEvent) -> None:
    logger.info(f"Beneficiary Core handling DossierApprovedEvent for DNI: {event.dni_reference}")
    try:
        async with async_session_maker() as session:
            repo = SqlBeneficiaryRepository(session)
            use_case = ProcessApprovedTriageCaseUseCase(repo)
            await use_case.execute(event)
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
                target_doc_type = f"Inscripción Educa {event.year}-1"
                
                # Update existing or append new
                existing_doc = next((d for d in beneficiary.historical_documents if d.document_type == target_doc_type and d.year == event.year), None)
                
                if existing_doc:
                    # Update file_id and batch_id (python dataclass frozen=True usually? Let's assume it's just object fields or we replace it)
                    # If HistoricalDocument is frozen, we replace the object
                    beneficiary.historical_documents.remove(existing_doc)
                    
                doc = HistoricalDocument(
                    id=existing_doc.id if existing_doc else uuid.uuid4(),
                    beneficiary_id=beneficiary.id,
                    batch_id=event.batch_id,
                    document_type=target_doc_type,
                    year=event.year,
                    file_id=event.pdf_id
                )
                beneficiary.historical_documents.append(doc)
                
                await repo.save(beneficiary)
                await session.commit()
                logger.info(f"Successfully saved historical PDF link for DNI: {event.beneficiary_dni}")
            else:
                logger.warning(f"Could not find beneficiary with DNI {event.beneficiary_dni} to attach PDF")
    except Exception as e:
        logger.error(f"Failed to save historical PDF for DNI {event.beneficiary_dni}: {str(e)}")
