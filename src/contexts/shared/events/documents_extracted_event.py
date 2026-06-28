# src/shared/events/documents_extracted.py
from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4


@dataclass
class DocumentsExtractedEvent:
    event_id: UUID = field(default_factory=uuid4)
    batch_id: UUID = None
    activity_type: str = None
    dni_reference: str = None
    version: str = "v1"
    event_name: str = "documents_extracted"
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
