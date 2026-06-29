from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID

@dataclass(frozen=True)
class DossierPdfArchivedEvent:
    beneficiary_dni: str
    triage_case_id: UUID
    pdf_url: str
    year: int
    event_name: str = field(default="DossierPdfArchivedEvent", init=False)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
