from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID
from pydantic import BaseModel, ConfigDict

class FieldMetadataSchema(BaseModel):
    name: str
    type: str
    label: str
    value: Optional[Any] = None
    is_editable: bool = True
    options: Optional[List[str]] = None
    group: Optional[str] = None

class DiscrepancySchema(BaseModel):
    field_name: str
    expected_pattern: Optional[str] = None
    actual_value: Optional[str] = None
    rule_description: str
    severity: str
    document_code: Optional[str] = None

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

class AuditLogEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    action: str
    performed_by: UUID
    previous_status: Optional[str] = None
    new_status: str
    details: Optional[Dict[str, Any]] = None
    created_at: datetime

class TriageCorrectionRequest(BaseModel):
    corrected_fields: Dict[str, Dict[str, Any]]

class TriageRejectRequest(BaseModel):
    reason: str

class BatchProcessingResult(BaseModel):
    batch_id: UUID
    total_dossiers: int
    total_documents: int
    auto_approved: int
    sent_to_triage: int
