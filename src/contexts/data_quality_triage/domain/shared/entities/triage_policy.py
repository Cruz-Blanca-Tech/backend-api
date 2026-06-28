from dataclasses import dataclass
from uuid import UUID
from typing import List

from src.contexts.data_quality_triage.domain.shared.entities.triage_case import TriageCase
from src.contexts.data_quality_triage.domain.shared.value_objects.validation_result import ValidationResult

@dataclass
class TriagePolicy:
    activity_id: UUID
    required_document_codes: List[str]

    def evaluate(self, case: TriageCase) -> ValidationResult:
        present = set(case.document_ids.keys())

        missing = [
            code for code in self.required_document_codes
            if code not in present
        ]

        return ValidationResult(
            is_valid=len(missing) == 0,
            missing_documents=missing,
            issues=[]
        )
