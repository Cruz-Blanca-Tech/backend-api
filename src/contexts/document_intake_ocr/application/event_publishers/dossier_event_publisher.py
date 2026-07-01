

from src.contexts.document_intake_ocr.domain.entities.activity import Activity
from src.contexts.document_intake_ocr.domain.entities.dossier import Dossier
from src.contexts.shared.events.documents_extracted_event import DocumentsExtractedEvent
from src.contexts.shared.events.batch_ocr_completed_event import BatchOcrCompletedEvent
from src.core.events.event_dispatcher import EventDispatcher

class DossierEventPublisher:
    async def publish_created(
        self,
        dossier: Dossier, 
        activity: Activity
    ) -> None:

        event = DocumentsExtractedEvent(
            batch_id=dossier.batch_id, 
            activity_type="EDUCA_INSCRIPTION",
            dni_reference=str(dossier.dni)
        )

        await EventDispatcher.dispatch(event)

    async def publish_batch_ocr_completed(self, batch_id) -> None:
        event = BatchOcrCompletedEvent(batch_id=batch_id)
        await EventDispatcher.dispatch(event)