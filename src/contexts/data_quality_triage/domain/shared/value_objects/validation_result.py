from dataclasses import dataclass, field
from typing import List

@dataclass
class ValidationResult:
    is_valid: bool
    missing_documents: List[str] = field(default_factory=list)
    issues: List[str] = field(default_factory=list)
