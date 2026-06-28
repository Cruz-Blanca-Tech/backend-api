from pydantic import BaseModel
from typing import List, Optional
from uuid import UUID

class DocumentDossierItemResponse(BaseModel):
    id: UUID
    code: Optional[str]
    file_name: str
    source_id: Optional[str]

class GetDocumentsByDossierResponse(BaseModel):
    documents: List[DocumentDossierItemResponse]
