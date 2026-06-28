from dataclasses import dataclass
from datetime import datetime
from typing import Optional


from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from enum import Enum


class DocumentStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING_OCR = "PROCESSING_OCR"
    READY_FOR_REVIEW = "READY_FOR_REVIEW"
    APPROVED = "APPROVED"
    FAILED = "FAILED"


@dataclass(frozen=True)
class PipelineState:
    status: DocumentStatus
    processed_at: Optional[datetime] = None        
    failure_reason: Optional[str] = None,


    @staticmethod
    def pending():
        return PipelineState(DocumentStatus.PENDING)

    def mark_processing(self):
        return PipelineState(DocumentStatus.PROCESSING_OCR, self.processed_at)

    def mark_success(self):
        return PipelineState(DocumentStatus.READY_FOR_REVIEW, datetime.utcnow())

    def mark_failed(self, reason: str) -> None: 
        self.failure_reason = reason
        return PipelineState(DocumentStatus.FAILED, self.processed_at)


    def mark_approved(self):
        return PipelineState(DocumentStatus.APPROVED, self.processed_at)