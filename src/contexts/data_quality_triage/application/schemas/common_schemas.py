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

class AuditLogEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    action: str
    performed_by: UUID
    previous_status: Optional[str] = None
    new_status: str
    details: Optional[Dict[str, Any]] = None
    created_at: datetime
