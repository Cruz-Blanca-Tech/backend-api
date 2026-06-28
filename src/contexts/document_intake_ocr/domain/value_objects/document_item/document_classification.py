from dataclasses import dataclass
from enum import Enum
from typing import Optional
from uuid import UUID

from src.contexts.document_intake_ocr.domain.value_objects.document_code import DocumentTypeCode

class ClassificationStatus(str, Enum):
    UNCLASSIFIED = "UNCLASSIFIED"
    CLASSIFIED = "CLASSIFIED"
    UNKNOWN = "UNKNOWN"
    
@dataclass(frozen=True)
class DocumentClassification:
    status: ClassificationStatus
    code: Optional[DocumentTypeCode]
    document_type_config_id: Optional[UUID]