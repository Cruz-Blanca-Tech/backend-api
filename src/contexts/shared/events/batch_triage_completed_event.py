from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List
from uuid import UUID

@dataclass(frozen=True)
class BatchTriageCompletedEvent:
    batch_id: UUID
    # Maps dni_reference -> {"corrected_dni": str, "documents": List[UUID]}
    approved_dossiers: Dict[str, dict]
    event_name: str = field(default="BatchTriageCompletedEvent", init=False)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
