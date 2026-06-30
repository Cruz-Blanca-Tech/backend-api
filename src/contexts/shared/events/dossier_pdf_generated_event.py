from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID

@dataclass(frozen=True)
class DossierPdfGeneratedEvent:
    batch_id: UUID
    dni: str
    document_type: str
    file_url: str
    year: int
    event_name: str = field(default="DossierPdfGeneratedEvent", init=False)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
