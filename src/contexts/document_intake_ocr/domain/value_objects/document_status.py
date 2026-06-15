from enum import Enum

class DocumentStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    QUALITY_CHECK = "quality_check"
    APPROVED = "approved"
    REJECTED = "rejected"
    MANUAL_REVIEW = "manual_review"
    
    @property
    def is_finalized(self) -> bool:
        return self in [DocumentStatus.APPROVED, DocumentStatus.REJECTED]