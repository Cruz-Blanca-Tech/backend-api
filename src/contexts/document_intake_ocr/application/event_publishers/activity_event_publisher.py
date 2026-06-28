from src.contexts.document_intake_ocr.domain.entities.activity import Activity
from src.contexts.shared.events.activity_requirements_configured_event import ActivityRequirementsConfiguredEvent
from src.contexts.shared.infrastructure.bus.event_bus import EventBus

class ActivityEventPublisher:

    def __init__(
        self,
        event_bus: EventBus
    ):
        self.event_bus = event_bus


    async def publish_created(
        self,
        activity: Activity
    ) -> None:

        event = ActivityRequirementsConfiguredEvent(
            activity_id=activity.id,
            program_id=activity.program_id,
            requirements=[
                req.code_str
                for req in activity.required_documents
            ]
        )

        await self.event_bus.publish(event)