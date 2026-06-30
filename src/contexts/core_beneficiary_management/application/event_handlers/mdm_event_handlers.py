import logging
from src.core.database import async_session_maker
from src.contexts.shared.events.dossier_approved_event import DossierApprovedEvent
from src.contexts.shared.events.dossier_pdf_generated_event import DossierPdfGeneratedEvent
from src.contexts.core_beneficiary_management.infrastructure.persistence.repositories.sql_beneficiary_repository import SqlBeneficiaryRepository
from src.contexts.core_beneficiary_management.application.use_cases.process_approved_triage_case_use_case import ProcessApprovedTriageCaseUseCase
from src.contexts.core_beneficiary_management.application.use_cases.save_historical_document_use_case import SaveHistoricalDocumentUseCase

logger = logging.getLogger(__name__)

async def handle_mdm_dossier_approved(event: DossierApprovedEvent) -> None:
    """
    Escucha cuando un expediente es aprobado en Triaje y actualiza/crea al Beneficiario en MDM.
    """
    logger.info(f"[MDM] Recibido DossierApprovedEvent para el caso {event.triage_case_id}. Actividad: {event.activity_type}")
    async with async_session_maker() as session:
        repo = SqlBeneficiaryRepository(session)
        use_case = ProcessApprovedTriageCaseUseCase(repo)
        try:
            await use_case.execute(event)
            await session.commit()
            logger.info(f"[MDM] Beneficiario procesado exitosamente para el caso {event.triage_case_id}.")
        except Exception as e:
            await session.rollback()
            logger.error(f"[MDM] Error procesando DossierApprovedEvent: {e}", exc_info=True)

async def handle_mdm_pdf_generated(event: DossierPdfGeneratedEvent) -> None:
    """
    Escucha cuando el OCR termina de generar el PDF y lo anexa al historial del Beneficiario.
    """
    logger.info(f"[MDM] Recibido DossierPdfGeneratedEvent para el DNI {event.dni}. Documento: {event.document_type}")
    async with async_session_maker() as session:
        repo = SqlBeneficiaryRepository(session)
        use_case = SaveHistoricalDocumentUseCase(repo)
        try:
            await use_case.execute(event)
            await session.commit()
            logger.info(f"[MDM] Documento Histórico guardado exitosamente para el DNI {event.dni}.")
        except Exception as e:
            await session.rollback()
            logger.error(f"[MDM] Error guardando documento histórico: {e}", exc_info=True)
