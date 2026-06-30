from pydantic import BaseModel
from typing import Optional
from uuid import UUID

class HistoricalDocumentResponse(BaseModel):
    id: UUID
    batch_id: Optional[UUID] = None
    document_type: str
    year: int
    file_id: str
