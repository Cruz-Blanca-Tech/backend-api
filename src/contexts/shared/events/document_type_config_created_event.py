# src/shared/events/policy_events.py
from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID

@dataclass
class DocumentTypeConfigCreatedEvent:
    document_type_id: UUID
    code: str
    name: str
    version: int
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    event_name: str = "document_type_created"