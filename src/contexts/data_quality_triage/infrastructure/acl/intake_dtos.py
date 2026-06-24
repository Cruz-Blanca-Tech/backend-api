from dataclasses import dataclass
from typing import Optional, Dict, Any
from uuid import UUID

@dataclass
class DocumentReadDTO:
    id: UUID
    batch_id: UUID
    document_code: str
    file_name: str
    dni_reference: str
    extracted_data: Dict[str, Any]
    confidence_score: Optional[float]
