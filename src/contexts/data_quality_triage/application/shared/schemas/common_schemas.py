from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID
from pydantic import BaseModel, ConfigDict

class DiscrepancySchema(BaseModel):
    field_name: str
    expected_pattern: Optional[str] = None
    actual_value: Optional[str] = None
    rule_description: str
    severity: str
    document_code: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict) -> "DiscrepancySchema":
        """Mapeo explícito (Anti-Corruption Layer) desde el JSONB de la BD hacia el Schema."""
        return cls(
            field_name=data.get("field_name", "Desconocido"),
            expected_pattern=data.get("expected_pattern"),
            actual_value=data.get("actual_value"),
            rule_description=data.get("rule_description", "Sin descripción"),
            severity=data.get("severity", "WARNING"),
            document_code=data.get("document_code")
        )
class AuditLogEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    action: str
    performed_by: UUID
    previous_status: Optional[str] = None
    new_status: str
    details: Optional[Dict[str, Any]] = None
    created_at: datetime
