import logging
import asyncio
from uuid import UUID
from typing import Dict, Any, List
from sqlalchemy import update, select

from src.core.database import async_session_maker
from src.contexts.data_quality_triage.domain.shared.repositories.triage_repository import TriageRepository
from src.contexts.data_quality_triage.domain.shared.value_objects.triage_status import TriageStatus, BatchVerificationStatus
from src.contexts.shared.events.dossier_approved_event import DossierApprovedEvent
from src.contexts.shared.events.batch_triage_completed_event import BatchTriageCompletedEvent
from src.core.events.event_dispatcher import EventDispatcher
from src.contexts.core_beneficiary_management.application.event_handlers.mdm_event_handlers import handle_mdm_dossier_approved
from src.contexts.document_intake_ocr.application.event_handlers.intake_event_handlers import handle_dossier_approved
from src.contexts.document_intake_ocr.infrastructure.persistence.model.extraction_batch_model import ExtractionBatchModel

logger = logging.getLogger(__name__)

class RetryBatchSyncUseCase:
    def __init__(self, triage_repo: TriageRepository):
        self.triage_repo = triage_repo

    async def execute(self, batch_id: UUID) -> Dict[str, Any]:
        cases = await self.triage_repo.get_all_by_batch_id(batch_id)
        if not cases:
            return {"status": "NOT_FOUND", "message": f"No se encontraron casos para el lote {batch_id}"}

        failed_cases = [
            c for c in cases
            if c.status == TriageStatus.APPROVED and c.sync_status != "SYNCED"
        ]

        if not failed_cases:
            # Si todos ya están sincronizados, aseguramos que el lote esté FINALIZED
            async with async_session_maker() as session:
                await session.execute(
                    update(ExtractionBatchModel)
                    .where(ExtractionBatchModel.id == batch_id)
                    .values(status="FINALIZED", failure_reason=None)
                )
                await session.commit()
            return {
                "status": "COMPLETED",
                "message": "Todos los expedientes del lote ya están sincronizados correctamente.",
                "reprocessed_count": 0
            }

        # Cambiar temporalmente a SYNCING
        async with async_session_maker() as session:
            await session.execute(
                update(ExtractionBatchModel)
                .where(ExtractionBatchModel.id == batch_id)
                .values(status="SYNCING")
            )
            await session.commit()

        sync_errors: List[Dict[str, Any]] = []
        approved_dossiers = {}

        for c in cases:
            if c.status == TriageStatus.APPROVED:
                corrected_dni = c.dossier_data.get("beneficiary", {}).get("dni", c.dni_reference)
                approved_dossiers[c.dni_reference] = {
                    "corrected_dni": corrected_dni,
                    "documents": list(c.document_ids.values())
                }

        for case in failed_cases:
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

            for attempt in range(1, 3):
                try:
                    await handle_mdm_dossier_approved(event)
                    await handle_dossier_approved(event)
                    success = True
                    break
                except Exception as err:
                    last_error = err
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
                failure_msg = f"{len(sync_errors)} expediente(s) aún no pudieron sincronizarse con Beneficiarios."
                await session.execute(
                    update(ExtractionBatchModel)
                    .where(ExtractionBatchModel.id == batch_id)
                    .values(status="SYNC_FAILED", failure_reason=failure_msg)
                )
                await session.commit()
                return {
                    "status": "SYNC_FAILED",
                    "message": failure_msg,
                    "failed_count": len(sync_errors),
                    "failed_cases": sync_errors
                }
            else:
                await session.execute(
                    update(ExtractionBatchModel)
                    .where(ExtractionBatchModel.id == batch_id)
                    .values(status="FINALIZED", failure_reason=None)
                )
                await session.commit()

                EventDispatcher.dispatch_background(BatchTriageCompletedEvent(
                    batch_id=batch_id,
                    approved_dossiers=approved_dossiers
                ))

                return {
                    "status": "COMPLETED",
                    "message": f"Todos los expedientes ({len(failed_cases)}) fueron reintentados y sincronizados exitosamente.",
                    "reprocessed_count": len(failed_cases)
                }
