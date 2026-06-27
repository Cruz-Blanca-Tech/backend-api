
from src.contexts.document_intake_ocr.domain.entities.document_type import DocumentTypeConfig
from src.contexts.shared.events.document_type_config_created_event import DocumentTypeConfigCreatedEvent
from src.contexts.shared.infrastructure.bus.event_bus import EventBus


class DocumentTypeConfigEventPublisher:

    def __init__(
        self,
        event_bus: EventBus
    ):
        self.event_bus = event_bus


    async def publish_created(
        self,
        document_type_config: DocumentTypeConfig
    ) -> None:

        event = DocumentTypeConfigCreatedEvent(
            document_type_id= document_type_config.id,
            name= document_type_config.name,
            version=document_type_config.version
        )

        await self.event_bus.publish(event)