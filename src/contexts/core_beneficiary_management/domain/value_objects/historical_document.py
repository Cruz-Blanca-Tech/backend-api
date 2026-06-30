from dataclasses import dataclass
from uuid import UUID
from typing import Optional

@dataclass
class HistoricalDocument:
    id: UUID
    beneficiary_id: UUID
    batch_id: Optional[UUID]
    document_type: str
    year: int
    file_id: str
