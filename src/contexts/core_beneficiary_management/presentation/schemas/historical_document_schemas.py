from pydantic import BaseModel
from typing import Optional
from uuid import UUID

class HistoricalDocumentResponse(BaseModel):
    id: UUID
    batch_id: UUID
    document_type: str
    year: int
    file_url: str
