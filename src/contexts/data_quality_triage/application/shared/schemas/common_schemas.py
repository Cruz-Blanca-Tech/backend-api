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
    def from_domain(cls, domain_obj: Any) -> "DiscrepancySchema":
        """Mapeo explícito (Anti-Corruption Layer) desde la Entidad de Dominio hacia el Schema."""
        return cls(
            field_name=getattr(domain_obj, "field_name", "Desconocido"),
            expected_pattern=getattr(domain_obj, "expected_pattern", None),
            actual_value=getattr(domain_obj, "actual_value", None),
            rule_description=getattr(domain_obj, "rule_description", "Sin descripción"),
            severity=getattr(domain_obj, "severity", "WARNING") if isinstance(getattr(domain_obj, "severity", "WARNING"), str) else getattr(domain_obj, "severity").value,
            document_code=getattr(domain_obj, "document_code", None)
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
