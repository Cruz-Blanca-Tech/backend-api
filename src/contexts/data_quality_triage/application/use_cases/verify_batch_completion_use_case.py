import logging
import asyncio
from uuid import UUID
from sqlalchemy import update

from src.core.database import async_session_maker
from src.contexts.data_quality_triage.domain.shared.ports.batch_status_validator import BatchStatusValidatorPort
from src.contexts.data_quality_triage.domain.shared.repositories.triage_repository import TriageRepository
from src.contexts.data_quality_triage.domain.shared.value_objects.triage_status import TriageVerdict, BatchVerificationStatus, TriageStatus
from src.contexts.shared.events.batch_triage_completed_event import BatchTriageCompletedEvent
from src.contexts.shared.events.dossier_approved_event import DossierApprovedEvent
from src.contexts.data_quality_triage.domain.shared.events.triage_events import DossierRejectedEvent
from src.core.events.event_dispatcher import EventDispatcher
from src.contexts.core_beneficiary_management.application.event_handlers.mdm_event_handlers import handle_mdm_dossier_approved
from src.contexts.document_intake_ocr.application.event_handlers.intake_event_handlers import (
    handle_dossier_approved, handle_dossier_rejected
)
from src.contexts.document_intake_ocr.infrastructure.persistence.model.extraction_batch_model import ExtractionBatchModel

logger = logging.getLogger(__name__)

class VerifyBatchCompletionUseCase:
    def __init__(self, triage_repository: TriageRepository, batch_status_validator: BatchStatusValidatorPort):
        self.triage_repository = triage_repository
        self.batch_status_validator = batch_status_validator

    async def execute(self, batch_id: UUID) -> dict:
        verdict_summary = {v.name: 0 for v in TriageVerdict}

        # Check if the batch is already completed
        is_completed = await self.batch_status_validator.is_batch_completed(batch_id)
        if is_completed:
            return {
                "status": BatchVerificationStatus.COMPLETED,
                "message": f"El lote {batch_id} ya fue verificado y completado previamente.",
                "verdict_summary": verdict_summary
            }

        # Check if the batch has finished processing in the OCR engine
        is_ready = await self.batch_status_validator.is_batch_ready_for_triage(batch_id)
        if not is_ready:
            return {
                "status": BatchVerificationStatus.PENDING,
                "message": "No se puede verificar la finalización porque el motor OCR aún está procesando el lote.",
                "verdict_summary": verdict_summary
            }

        cases = await self.triage_repository.get_all_by_batch_id(batch_id)
        logger.info(f"VerifyBatchCompletion - Loaded {len(cases)} cases for batch {batch_id}")
        
        if not cases:
            return {
                "status": BatchVerificationStatus.NOT_FOUND, 
                "message": f"No triage cases found for batch {batch_id}",
                "verdict_summary": verdict_summary
            }
        
        all_processed = True
        pending_cases = 0

        for case in cases:
            verdict_name = case.verdict.name if hasattr(case.verdict, 'name') else case.verdict
            verdict_summary[verdict_name] = verdict_summary.get(verdict_name, 0) + 1
            
            if case.verdict == TriageVerdict.REQUIRES_TRIAGE:
                all_processed = False
                pending_cases += 1
                
        if not all_processed:
            return {
                "status": BatchVerificationStatus.PENDING, 
                "message": f"El lote {batch_id} aún tiene {pending_cases} expediente(s) pendientes de revisión.",
                "verdict_summary": verdict_summary
            }

        # Marcar lote en estado de sincronización (SYNCING)
        async with async_session_maker() as session:
            await session.execute(
                update(ExtractionBatchModel)
                .where(ExtractionBatchModel.id == batch_id)
                .values(status="SYNCING")
            )
            await session.commit()

        # Procesar rechazos (marcar documentos como REJECTED)
        for case in cases:
            if case.status == TriageStatus.REJECTED:
                try:
                    rej_event = DossierRejectedEvent(
                        triage_case_id=case.id,
                        batch_id=case.batch_id,
                        dni_reference=case.dni_reference,
                        document_ids=list(case.document_ids.values()),
                        rejected_by=case.resolved_by or UUID("00000000-0000-0000-0000-000000000001"),
                        reason=case.rejection_reason or "Rechazado en triaje"
                    )
                    await handle_dossier_rejected(rej_event)
                except Exception as ex:
                    logger.error(f"Error procesando rechazo de caso {case.id}: {ex}")

        # Sincronizar aprobados con reintento automático
        sync_errors = []
        approved_dossiers = {}

        for case in cases:
            if case.status == TriageStatus.APPROVED:
                # Extraer DNI corregido
                corrected_dni = case.dossier_data.get("beneficiary", {}).get("dni", case.dni_reference)
                approved_dossiers[case.dni_reference] = {
                    "corrected_dni": corrected_dni,
                    "documents": list(case.document_ids.values())
                }

                # Si ya estaba sincronizado exitosamente, no repetimos
                if case.sync_status == "SYNCED":
                    continue

                event = DossierApprovedEvent(
                    triage_case_id=case.id,
                    batch_id=case.batch_id,
                    activity_type=case.activity_type,
                    dni_reference=case.dni_reference,
                    dossier_data=case.dossier_data,
                    approved_by=case.resolved_by or UUID("00000000-0000-0000-0000-000000000001")
                )

                success = False
                last_error = None

                # Intentos: 1 intento regular + 1 reintento automático con 500ms de backoff
                for attempt in range(1, 3):
                    try:
                        await handle_mdm_dossier_approved(event)
                        await handle_dossier_approved(event)
                        success = True
                        break
                    except Exception as err:
                        last_error = err
                        logger.warning(f"Intento {attempt}/2 falló para sincronizar caso {case.id} (DNI {case.dni_reference}): {err}")
                        if attempt == 1:
                            await asyncio.sleep(0.5)

                if not success:
                    sync_errors.append({
                        "case_id": str(case.id),
                        "dni": case.dni_reference,
                        "error": str(last_error)
                    })

        async with async_session_maker() as session:
            if sync_errors:
                # Hubo fallos: el lote NO se finaliza, se marca como SYNC_FAILED
                failure_msg = f"{len(sync_errors)} expediente(s) no pudieron sincronizarse con Beneficiarios."
                await session.execute(
                    update(ExtractionBatchModel)
                    .where(ExtractionBatchModel.id == batch_id)
                    .values(status="SYNC_FAILED", failure_reason=failure_msg)
                )
                await session.commit()

                logger.error(f"Lote {batch_id} finalizado con {len(sync_errors)} errores de sincronización.")
                return {
                    "status": BatchVerificationStatus.SYNC_FAILED,
                    "message": failure_msg,
                    "failed_count": len(sync_errors),
                    "failed_cases": sync_errors,
                    "verdict_summary": verdict_summary
                }
            else:
                # Todos los aprobados fueron sincronizados con éxito -> FINALIZED
                await session.execute(
                    update(ExtractionBatchModel)
                    .where(ExtractionBatchModel.id == batch_id)
                    .values(status="FINALIZED", failure_reason=None)
                )
                await session.commit()

                # Disparar generación masiva de PDFs en background
                EventDispatcher.dispatch_background(BatchTriageCompletedEvent(
                    batch_id=batch_id,
                    approved_dossiers=approved_dossiers
                ))

                logger.info(f"Lote {batch_id} verificado y FINALIZADO exitosamente.")
                return {
                    "status": BatchVerificationStatus.COMPLETED,
                    "message": f"Lote {batch_id} verificado y cargado exitosamente. Todos los beneficiarios han sido creados.",
                    "verdict_summary": verdict_summary
                }
