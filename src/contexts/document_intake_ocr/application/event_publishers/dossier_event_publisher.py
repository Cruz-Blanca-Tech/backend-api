

from src.contexts.document_intake_ocr.domain.entities.activity import Activity
from src.contexts.document_intake_ocr.domain.entities.dossier import Dossier
from src.contexts.shared.events.documents_extracted_event import DocumentsExtractedEvent
from src.core.events.event_dispatcher import EventDispatcher

class DossierEventPublisher:
    async def publish_created(
        self,
        dossier: Dossier, 
        activity: Activity
    ) -> None:

        event = DocumentsExtractedEvent(
            batch_id=dossier.batch_id, 
            activity_id=activity.id,
            dni_reference=str(dossier.dni)
        )

        await EventDispatcher.dispatch(event)