import logging
from src.core.events.event_dispatcher import EventDispatcher
from src.contexts.data_quality_triage.domain.shared.events.triage_events import DossierRejectedEvent, BatchRejectedEvent
from src.contexts.shared.events.dossier_approved_event import DossierApprovedEvent
from src.contexts.shared.events.dossier_pdf_generated_event import DossierPdfGeneratedEvent
from src.contexts.shared.events.documents_extracted_event import DocumentsExtractedEvent
from src.contexts.document_intake_ocr.application.event_handlers.intake_event_handlers import (
    handle_dossier_approved, handle_dossier_rejected, handle_batch_rejected
)
from src.contexts.data_quality_triage.application.shared.handlers.triage_event_handler import handle_documents_extracted
from src.contexts.core_beneficiary_management.application.event_handlers.mdm_event_handlers import (
    handle_mdm_dossier_approved, handle_mdm_pdf_generated
)

logger = logging.getLogger(__name__)

def bootstrap_event_subscribers() -> None:
    """
    Componente central de inicialización. 
    Registra todos los interceptores y manejadores de eventos del sistema (Coreography).
    """
    # 1. Eventos desde Triage hacia OCR
    EventDispatcher.register(DossierApprovedEvent, handle_dossier_approved)
    EventDispatcher.register(DossierRejectedEvent, handle_dossier_rejected)
    EventDispatcher.register(BatchRejectedEvent, handle_batch_rejected)
    
    # 2. Eventos desde OCR hacia Triage
    EventDispatcher.register(DocumentsExtractedEvent, handle_documents_extracted)
    
    # 3. Eventos hacia Beneficiarios (MDM)
    EventDispatcher.register(DossierApprovedEvent, handle_mdm_dossier_approved)
    EventDispatcher.register(DossierPdfGeneratedEvent, handle_mdm_pdf_generated)
    
    logger.info("[Bootstrap] Todos los suscriptores de eventos han sido registrados exitosamente.")