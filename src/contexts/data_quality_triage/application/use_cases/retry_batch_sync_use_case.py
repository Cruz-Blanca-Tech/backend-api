import logging
import asyncio
from uuid import UUID
from typing import Dict, Any, List
from sqlalchemy import update, select

from src.core.database import async_session_maker
from src.contexts.data_quality_triage.domain.shared.repositories.triage_repository import TriageRepository
from src.contexts.data_quality_triage.domain.shared.value_objects.triage_status import TriageStatus, BatchVerificationStatus
from src.contexts.data_quality_triage.application.shared.use_cases.finalize_batch_if_complete_use_case import (
    FinalizeBatchIfCompleteUseCase,
)
from src.contexts.shared.events.dossier_approved_event import DossierApprovedEvent
from src.contexts.shared.events.batch_triage_completed_event import BatchTriageCompletedEvent
from src.core.events.event_dispatcher import EventDispatcher
from src.contexts.core_beneficiary_management.application.event_handlers.mdm_event_handlers import handle_mdm_dossier_approved
from src.contexts.document_intake_ocr.application.event_handlers.intake_event_handlers import handle_dossier_approved

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
            # No hay nada que reintentar. El estado del lote lo decide la regla
            # común, NO esta respuesta: antes esta rama ponía FINALIZED sin mirar
            # si quedaban expedientes sin decidir, así que reintentar sobre un lote
            # a medio triage cerraba el lote de golpe. Con un lote todavía abierto
            # esta operación es un no-op y el lote sigue como estaba.
            async with async_session_maker() as session:
                estado = await FinalizeBatchIfCompleteUseCase(
                    session=session, triage_repo=self.triage_repo
                ).execute(batch_id)
                await session.commit()
            return {
                "status": estado or "PENDING",
                "message": "No hay expedientes pendientes de sincronizar en este lote.",
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
            # El estado del lote lo decide la regla común, por el mismo motivo que
            # en la rama de arriba: acá ya no se sincroniza nada, solo queda derivar
            # si el lote se cierra. Poner FINALIZED a mano cerraría un lote que
            # todavía tiene expedientes sin revisar.
            estado_lote = await FinalizeBatchIfCompleteUseCase(
                session=session, triage_repo=self.triage_repo
            ).execute(batch_id)
            await session.commit()

            if sync_errors:
                # Los errores por expediente van en la respuesta y en la ficha de
                # cada caso (`sync_error`), que es donde se reintenta uno por uno.
                # El lote conserva en `failure_reason` el detalle que escribió la
                # regla común.
                failure_msg = f"{len(sync_errors)} expediente(s) aún no pudieron sincronizarse con Beneficiarios."
                return {
                    "status": "SYNC_FAILED",
                    "message": failure_msg,
                    "failed_count": len(sync_errors),
                    "failed_cases": sync_errors
                }

            if estado_lote == "FINALIZED":
                EventDispatcher.dispatch_background(BatchTriageCompletedEvent(
                    batch_id=batch_id,
                    approved_dossiers=approved_dossiers
                ))
                return {
                    "status": "FINALIZED",
                    "message": (
                        f"Todos los expedientes ({len(failed_cases)}) fueron reintentados y "
                        "cargados. El lote quedó cerrado."
                    ),
                    "reprocessed_count": len(failed_cases)
                }

            return {
                "status": estado_lote or "PENDING",
                "message": (
                    f"Todos los expedientes ({len(failed_cases)}) fueron reintentados y "
                    "cargados, pero el lote todavía tiene expedientes sin decidir."
                ),
                "reprocessed_count": len(failed_cases)
            }
