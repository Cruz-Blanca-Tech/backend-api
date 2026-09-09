import logging
from uuid import UUID
from typing import Dict, Any
from sqlalchemy import update

from src.core.database import async_session_maker
from src.contexts.data_quality_triage.domain.shared.repositories.triage_repository import TriageRepository
from src.contexts.data_quality_triage.domain.shared.value_objects.triage_status import TriageStatus
from src.contexts.shared.events.dossier_approved_event import DossierApprovedEvent
from src.contexts.core_beneficiary_management.application.event_handlers.mdm_event_handlers import handle_mdm_dossier_approved
from src.contexts.document_intake_ocr.application.event_handlers.intake_event_handlers import handle_dossier_approved
from src.contexts.document_intake_ocr.infrastructure.persistence.model.extraction_batch_model import ExtractionBatchModel

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

        # Verificar si todos los casos aprobados de su lote ya están en SYNCED
        all_cases = await self.triage_repo.get_all_by_batch_id(case.batch_id)
        pending_or_failed = [
            c for c in all_cases
            if c.status == TriageStatus.APPROVED and c.id != case.id and c.sync_status != "SYNCED"
        ]

        if not pending_or_failed:
            async with async_session_maker() as session:
                await session.execute(
                    update(ExtractionBatchModel)
                    .where(ExtractionBatchModel.id == case.batch_id)
                    .values(status="FINALIZED", failure_reason=None)
                )
                await session.commit()
                logger.info(f"Lote {case.batch_id} promovido a FINALIZED tras sincronizar su último caso pendiente.")

        return {
            "status": "SYNCED",
            "message": f"El expediente {case.dni_reference} fue sincronizado exitosamente con Beneficiarios."
        }
