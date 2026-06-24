from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID
from pydantic import BaseModel, ConfigDict

from .common_schemas import FieldMetadataSchema, DiscrepancySchema

class TriageCaseListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    batch_id: UUID
    dni_reference: str
    status: str
    verdict: str
    min_confidence_score: float
    confidence_threshold: float
    error_count: int
    warning_count: int
    created_at: datetime
    updated_at: Optional[datetime] = None

class TriageCaseDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    batch_id: UUID
    dni_reference: str
    status: str
    verdict: str
    confidence_scores: Dict[str, float]
    confidence_threshold: float
    documents_snapshot: Dict[str, Dict[str, Any]]
    corrected_data: Optional[Dict[str, Dict[str, Any]]] = None
    effective_data: Dict[str, Dict[str, Any]]
    metadata_schema: Dict[str, List[FieldMetadataSchema]]
    discrepancies: List[DiscrepancySchema]
    rejection_reason: Optional[str] = None
    resolved_by: Optional[UUID] = None
    resolved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

class PaginatedTriageResponse(BaseModel):
    items: List[TriageCaseListItem]
    total: int
    skip: int
    limit: int

class BatchTriageSummary(BaseModel):
    batch_id: UUID
    total_dossiers: int
    auto_approved: int
    pending_review: int
    manually_approved: int
    rejected: int

class BatchProcessingResult(BaseModel):
    batch_id: UUID
    total_dossiers: int
    total_documents: int
    auto_approved: int
    sent_to_triage: int
