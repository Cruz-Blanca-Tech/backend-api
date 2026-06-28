# src/contexts/data_quality_triage/application/handlers/triage_event_handler.py

import logging
from src.contexts.shared.events.documents_extracted_event import DocumentsExtractedEvent
from src.contexts.data_quality_triage.application.shared.services.dossier_processor import ProcessDossierUseCase

logger = logging.getLogger(__name__)

class TriageEventHandler:
    def __init__(self, process_dossier_use_case: ProcessDossierUseCase):
        self.process_dossier_use_case = process_dossier_use_case

    async def handle(self, event: DocumentsExtractedEvent) -> None:
        """
        Reacciona al evento que emite Ingesta (BC2). Ejecuta la Fase 1: Creación y Política de validación cruzada.
        """
        logger.info(f"Procesando DNI {event.dni_reference} del batch {event.batch_id} con actividad {event.activity_type}")
        await self.process_dossier_use_case.execute(
            dni=event.dni_reference,
            batch_id=event.batch_id,
            activity_type_str=event.activity_type
        )
        logger.info(f"DNI {event.dni_reference} procesado exitosamente en triaje.")

async def handle_documents_extracted(event) -> None:
    """
    Punto de entrada global para el Bus de Eventos.
    Abre una sesión de base de datos aislada, resuelve las dependencias y ejecuta el Triage.
    """
    from src.core.database import async_session_maker
    from src.contexts.data_quality_triage.infrastructure.dependencies.triage_deps import get_triage_repository
    from src.contexts.data_quality_triage.infrastructure.persistence.repositories.sql_document_read_repository import SqlDocumentReadRepository
    from src.contexts.data_quality_triage.domain.shared.strategies.triage_strategy_factory import TriageStrategyFactory
    
    logger.info(f"[Triage Event Handler] Escuchando DocumentsExtractedEvent para batch {event.batch_id} y DNI {event.dni_reference}")
    
    async with async_session_maker() as session:
        # Resolver dependencias manualmente
        repo = get_triage_repository(session)
        doc_repo = SqlDocumentReadRepository(session)
        strategy_factory = TriageStrategyFactory()
        
        use_case = ProcessDossierUseCase(
            triage_repo=repo,
            doc_repo=doc_repo,
            strategy_factory=strategy_factory,
            session=session
        )
        
        handler = TriageEventHandler(process_dossier_use_case=use_case)
        await handler.handle(event)
        
        # Guardar en base de datos
        await session.commit()