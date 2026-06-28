from dataclasses import dataclass, field
from typing import List, Dict, Any
from src.contexts.data_quality_triage.domain.shared.value_objects.field_discrepancy import FieldDiscrepancy

@dataclass(frozen=True)
class QualityRuleResult:
    is_valid: bool
    discrepancies: List[FieldDiscrepancy] = field(default_factory=list)
    confidence_passed: bool = True
    enriched_docs: Dict[str, Any] = field(default_factory=dict)

    @property
    def has_errors(self) -> bool:
        return any(d.severity == "ERROR" for d in self.discrepancies)

    @property
    def error_count(self) -> int:
        return sum(1 for d in self.discrepancies if d.severity == "ERROR")

    @property
    def warning_count(self) -> int:
        return sum(1 for d in self.discrepancies if d.severity == "WARNING")
