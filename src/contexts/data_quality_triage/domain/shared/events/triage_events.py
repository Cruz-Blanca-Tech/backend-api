from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List
from uuid import UUID

@dataclass(frozen=True)
class DocumentApprovedEvent:
    document_id: UUID
    triage_case_id: UUID
    approved_by: UUID
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

@dataclass(frozen=True)
class DocumentRejectedEvent:
    document_id: UUID
    triage_case_id: UUID
    rejected_by: UUID
    reason: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))



@dataclass(frozen=True)
class DossierRejectedEvent:
    triage_case_id: UUID
    batch_id: UUID
    dni_reference: str
    document_ids: List[UUID]
    rejected_by: UUID
    reason: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

@dataclass(frozen=True)
class BatchRejectedEvent:
    batch_id: UUID
    triage_case_ids: List[UUID]
    document_ids: List[UUID]
    rejected_by: UUID
    reason: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
