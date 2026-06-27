

from src.contexts.document_intake_ocr.domain.entities.activity import Activity
from src.contexts.document_intake_ocr.domain.entities.dossier import Dossier
from src.contexts.shared.events.documents_extracted_event import DocumentsExtractedEvent
from src.contexts.shared.infrastructure.bus.event_bus import EventBus

class DossierEventPublisher:

    def __init__(
        self,
        event_bus: EventBus
    ):
        self.event_bus = event_bus


    async def publish_created(
        self,
        dossier: Dossier, 
        activity: Activity
    ) -> None:

        event = DocumentsExtractedEvent(
            batch_id=dossier.batch_id, # Asumiendo que tu dossier tiene el batch_id
            activity_id=activity.id,
            dni_reference=str(dossier.dni)
        )

        await self.event_bus.publish(event)