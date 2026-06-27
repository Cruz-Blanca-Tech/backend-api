# src/contexts/data_quality_triage/application/handlers/activity_created_handler.py
from src.contexts.data_quality_triage.domain.entities.triage_policy import TriagePolicy
from src.contexts.data_quality_triage.domain.repositories.policy_repository import PolicyRepository
from src.contexts.shared.events.activity_requirements_configured_event import ActivityCreatedEvent


# src/contexts/data_quality_triage/application/handlers/activity_created_handler import ActivityCreatedEvent
from sqlalchemy.ext.asyncio import async_sessionmaker

class ActivityCreatedHandler:
    def __init__(self, session_factory: async_sessionmaker):
        self.session_factory = session_factory

    async def handle(self, event: ActivityCreatedEvent) -> None:
        # Abrimos una sesión dedicada única para este evento (como lo haría un worker de Kafka)
        async with self.session_factory() as session:
            policy_repo = PolicyRepository(session)
            
            policy = TriagePolicy(
                program_id=event.program_id,
                required_document_codes=event.requirements
            )
            await policy_repo.save(policy)