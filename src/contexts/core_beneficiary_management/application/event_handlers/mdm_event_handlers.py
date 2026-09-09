import logging
from src.core.database import async_session_maker
from src.contexts.shared.events.dossier_approved_event import DossierApprovedEvent
from src.contexts.shared.events.dossier_pdf_generated_event import DossierPdfGeneratedEvent
from src.contexts.core_beneficiary_management.infrastructure.persistence.repositories.sql_beneficiary_repository import SqlBeneficiaryRepository
from src.contexts.core_beneficiary_management.application.use_cases.process_approved_triage_case_use_case import ProcessApprovedTriageCaseUseCase
from src.contexts.core_beneficiary_management.application.use_cases.save_historical_document_use_case import SaveHistoricalDocumentUseCase

logger = logging.getLogger(__name__)

from uuid import uuid4
from sqlalchemy import update
from src.contexts.shared.application.services.dead_letter_service import DeadLetterService
from src.contexts.data_quality_triage.infrastructure.persistence.model.triage_case_model import TriageCaseModel
from src.contexts.data_quality_triage.infrastructure.persistence.model.triage_audit_log_model import TriageAuditLogModel

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
            # Actualizamos el estado de sincronización del caso en Triaje a SYNCED
            await session.execute(
                update(TriageCaseModel)
                .where(TriageCaseModel.id == event.triage_case_id)
                .values(sync_status="SYNCED", sync_error=None)
            )
            await DeadLetterService.mark_resolved(session, event.triage_case_id, "handle_mdm_dossier_approved")
            await session.commit()
            logger.info(f"[MDM] Beneficiario procesado exitosamente para el caso {event.triage_case_id}.")
        except Exception as e:
            await session.rollback()
            logger.error(f"[MDM] Error procesando DossierApprovedEvent para caso {event.triage_case_id}: {e}", exc_info=True)
            try:
                async with async_session_maker() as err_session:
                    await DeadLetterService.record_failure(
                        err_session,
                        event=event,
                        handler_name="handle_mdm_dossier_approved",
                        error=e,
                        aggregate_id=event.triage_case_id
                    )
                    await err_session.execute(
                        update(TriageCaseModel)
                        .where(TriageCaseModel.id == event.triage_case_id)
                        .values(sync_status="FAILED", sync_error=str(e)[:1000])
                    )
                    audit_log = TriageAuditLogModel(
                        id=uuid4(),
                        triage_case_id=event.triage_case_id,
                        action="MDM_SYNC_FAILED",
                        performed_by=event.approved_by,
                        previous_status="APPROVED",
                        new_status="APPROVED",
                        details={"error": str(e)}
                    )
                    err_session.add(audit_log)
                    await err_session.commit()
            except Exception as log_err:
                logger.error(f"[MDM] Error al registrar fallo en DeadLetter / TriageCase: {log_err}", exc_info=True)
            raise e

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
