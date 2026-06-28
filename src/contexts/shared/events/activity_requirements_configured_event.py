# src/contexts/document_intake_ocr/domain/events/activity_created.py
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List
from uuid import UUID

@dataclass
class ActivityRequirementsConfiguredEvent:
    activity_id: UUID
    required_document_codes: list[str]
    event_name: str = "DossierCreated"
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
