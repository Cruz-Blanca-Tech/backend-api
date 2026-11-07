from dataclasses import dataclass
from typing import Dict, Any, Optional
from uuid import UUID

@dataclass
class DocumentDTO:
    id: UUID
    file_name: str
    document_code: Optional[str]
    extracted_data: Dict[str, Any]
    confidence_score: Optional[float]
    status: Optional[str] = None
    failure_reason: Optional[str] = None