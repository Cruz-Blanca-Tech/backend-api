# src/core/bootstrap.py
from src.contexts.data_quality_triage.application.handlers.triage_event_handler import TriageEventHandler
from src.contexts.data_quality_triage.infrastructure.dependencies.triage_deps import get_triage_service
from src.contexts.shared.events.activity_requirements_configured_event import ActivityCreatedEvent
from src.contexts.shared.events.documents_extracted_event import DocumentsExtractedEvent
from src.contexts.shared.infrastructure.bus.event_bus import EventBus
from src.core.database import async_session_maker # Tu objeto sessionmaker de SQLAlchemy
from src.contexts.data_quality_triage.application.handlers.activity_created_handler import ActivityCreatedHandler

def bootstrap_event_subscribers(event_bus: EventBus) -> None:
    """
    Componente central de inicialización. 
    Registra todos los interceptores y manejadores de eventos del sistema.
    """
    # 1. Instanciamos el Handler de Triaje pasándole la fábrica de conexiones
    triage_service = get_triage_service()
    triage_handler = TriageEventHandler(triage_service)
    # 2. Suscribimos al nuevo evento
    event_bus.subscribe(DocumentsExtractedEvent, triage_handler.handle)
    
    triage_handler = ActivityCreatedHandler(async_session_maker)
    
    # 2. Realizamos la suscripción en el bus
    event_bus.subscribe(ActivityCreatedEvent, triage_handler.handle)
    
    # Nota: Si mañana creas más contextos que escuchen eventos, los registras AQUÍ,
    # manteniendo tu main.py intacto.