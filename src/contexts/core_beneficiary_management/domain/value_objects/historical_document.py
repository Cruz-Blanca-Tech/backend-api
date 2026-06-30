from dataclasses import dataclass
from uuid import UUID

@dataclass
class HistoricalDocument:
    id: UUID
    beneficiary_id: UUID
    batch_id: UUID
    document_type: str
    year: int
    file_url: str
