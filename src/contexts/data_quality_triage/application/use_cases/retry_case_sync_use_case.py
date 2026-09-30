import logging
from uuid import UUID
from typing import Dict, Any

from src.core.database import async_session_maker
from src.contexts.data_quality_triage.domain.shared.repositories.triage_repository import TriageRepository
from src.contexts.data_quality_triage.domain.shared.value_objects.triage_status import TriageStatus
from src.contexts.data_quality_triage.application.shared.use_cases.finalize_batch_if_complete_use_case import (
    FinalizeBatchIfCompleteUseCase,
)
from src.contexts.shared.events.dossier_approved_event import DossierApprovedEvent
from src.contexts.core_beneficiary_management.application.event_handlers.mdm_event_handlers import handle_mdm_dossier_approved
from src.contexts.document_intake_ocr.application.event_handlers.intake_event_handlers import handle_dossier_approved

logger = logging.getLogger(__name__)

class RetryCaseSyncUseCase:
    def __init__(self, triage_repo: TriageRepository):
        self.triage_repo = triage_repo

    async def execute(self, case_id: UUID) -> Dict[str, Any]:
        case = await self.triage_repo.get_by_id(case_id)
        if not case:
            raise ValueError(f"No se encontró el caso de triaje con ID {case_id}")

        if case.status != TriageStatus.APPROVED:
            raise ValueError(f"Solo se puede sincronizar un caso que esté en estado APPROVED (actual: {case.status})")

        # El reintento existe para cuando la carga falló. Si el expediente ya está
        # en MDM no hay nada que reintentar: volver a correr el handler escribiría
        # dos veces sobre el mismo beneficiario.
        if (case.sync_status or "PENDING") == "SYNCED":
            raise ValueError(
                f"El expediente {case.dni_reference} ya está cargado en el registro de "
                "beneficiarios, no hay nada que reintentar."
            )

        event = DossierApprovedEvent(
            triage_case_id=case.id,
            batch_id=case.batch_id,
            activity_type=case.activity_type,
            dni_reference=case.dni_reference,
            dossier_data=case.dossier_data,
            approved_by=case.resolved_by or UUID("00000000-0000-0000-0000-000000000001")
        )

        try:
            await handle_mdm_dossier_approved(event)
            await handle_dossier_approved(event)
        except Exception as e:
            logger.error(f"Error al reintentar sincronización del caso {case_id}: {e}")
            raise ValueError(f"Fallo al sincronizar con Beneficiarios: {str(e)}")

        # El lote puede haber quedado esperando por este caso: si era el último,
        # pasa a FINALIZED (o a SYNC_FAILED si hay otros que tampoco llegaron).
        async with async_session_maker() as session:
            estado_lote = await FinalizeBatchIfCompleteUseCase(
                session=session, triage_repo=self.triage_repo
            ).execute(case.batch_id)
            await session.commit()

        mensaje = f"El expediente {case.dni_reference} fue sincronizado exitosamente con Beneficiarios."
        if estado_lote == "FINALIZED":
            mensaje += " El lote quedó cerrado: todos sus expedientes están rechazados y/o cargados."
        elif estado_lote == "SYNC_FAILED":
            mensaje += " El lote sigue esperando a que los demás expedientes lleguen al registro de beneficiarios."

        return {
            "status": "SYNCED",
            "message": mensaje,
        }
