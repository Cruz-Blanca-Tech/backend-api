from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID
from typing import Optional

@dataclass(frozen=True)
class DossierPdfArchivedEvent:
    beneficiary_dni: str
    triage_case_id: UUID
    pdf_id: str
    year: int
    batch_id: Optional[UUID] = None
    event_name: str = field(default="DossierPdfArchivedEvent", init=False)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
