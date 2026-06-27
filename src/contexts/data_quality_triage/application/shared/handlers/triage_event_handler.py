# src/contexts/data_quality_triage/application/handlers/triage_event_handler.py

import logging
from src.contexts.data_quality_triage.domain.shared.entities.triage_case import TriageStatus
from src.contexts.shared.events.documents_extracted_event import DocumentsExtractedEvent
from src.contexts.data_quality_triage.application.shared.use_cases.create_dossier_use_case import CreateDossierUseCase

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
        if response.status == TriageStatus.PENDING_REVIEW.value:
            logger.warning(f"Batch {event.batch_id} - DNI {event.dni_reference} requiere corrección (status: {response.status}).")
        else:
            logger.info(f"Batch {event.batch_id} - DNI {event.dni_reference} procesado exitosamente (status: {response.status}).")

async def handle_documents_extracted(event) -> None:
    """
    Punto de entrada global para el Bus de Eventos.
    Abre una sesión de base de datos aislada, resuelve las dependencias y ejecuta el Triage.
    """
    from src.core.database import async_session_maker
    from src.contexts.data_quality_triage.infrastructure.dependencies.triage_deps import get_triage_repository, get_dossier_processor
    from src.contexts.data_quality_triage.infrastructure.port.intake_document_provider import IntakeDocumentProvider
    from src.contexts.data_quality_triage.application.shared.use_cases.create_dossier_use_case import CreateDossierUseCase
    from src.contexts.data_quality_triage.domain.educa.services.educa_inscription_policy import EducaInscriptionPolicy
    
    logger.info(f"[Triage Event Handler] Escuchando DocumentsExtractedEvent para batch {event.batch_id} y DNI {event.dni_reference}")
    
    async with async_session_maker() as session:
        # Resolver dependencias manualmente
        repo = get_triage_repository(session)
        doc_provider = IntakeDocumentProvider(session=session)
        policy = EducaInscriptionPolicy()
        
        use_case = CreateDossierUseCase(
            doc_provider=doc_provider,
            case_repo=repo,
            policy=policy
        )
        
        handler = TriageEventHandler(create_dossier_use_case=use_case)
        await handler.handle(event)
        
        # Guardar en base de datos
        await session.commit()