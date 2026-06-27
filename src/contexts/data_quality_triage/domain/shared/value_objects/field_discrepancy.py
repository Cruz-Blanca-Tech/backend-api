from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class FieldDiscrepancy:
    field_name: str
    expected_pattern: Optional[str]
    actual_value: Optional[str]
    rule_description: str
    severity: str
    document_code: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "field_name": self.field_name,
            "expected_pattern": self.expected_pattern,
            "actual_value": self.actual_value,
            "rule_description": self.rule_description,
            "severity": self.severity,
            "document_code": self.document_code,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "FieldDiscrepancy":
        return cls(
            field_name=data["field_name"],
            expected_pattern=data.get("expected_pattern"),
            actual_value=data.get("actual_value"),
            rule_description=data["rule_description"],
            severity=data["severity"],
            document_code=data.get("document_code"),
        )
