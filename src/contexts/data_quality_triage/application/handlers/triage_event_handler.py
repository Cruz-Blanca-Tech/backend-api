# src/contexts/data_quality_triage/application/handlers/triage_event_handler.py

import logging
from src.contexts.data_quality_triage.domain.entities.triage_case import TriageStatus
from src.contexts.shared.events.documents_extracted_event import DocumentsExtractedEvent
from src.contexts.data_quality_triage.application.use_cases.create_dossier_use_case import CreateDossierUseCase

logger = logging.getLogger(__name__)

class TriageEventHandler:
    def __init__(self, create_dossier_use_case: CreateDossierUseCase):
        self.create_dossier_use_case = create_dossier_use_case

    async def handle(self, event: DocumentsExtractedEvent) -> None:
        """
        Reacciona al evento que emite Ingesta (BC2). Ejecuta la Fase 1: Creación y Política de validación cruzada.
        """
        response = await self.create_dossier_use_case.execute(
            batch_id=event.batch_id,
            dni=event.dni_reference,
            activity_id=event.activity_id
        )
        if response.status == TriageStatus.PENDING_CORRECTION.value:
            logger.warning(f"Se generó un caso PENDING_CORRECTION para {event.dni_reference} con {len(response.issues)} inconsistencias.")