from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID

@dataclass(frozen=True)
class BatchTriageCompletedEvent:
    batch_id: UUID
    event_name: str = field(default="BatchTriageCompletedEvent", init=False)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
