from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID

@dataclass(frozen=True)
class DossierApprovedEvent:
    triage_case_id: UUID
    batch_id: UUID
    activity_type: str
    dni_reference: str
    dossier_data: dict
    approved_by: UUID
    event_name: str = field(default="DossierApprovedEvent", init=False)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
