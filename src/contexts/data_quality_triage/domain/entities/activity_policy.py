# src/contexts/data_quality_triage/domain/entities/triage_policy.py
from dataclasses import dataclass
from uuid import UUID
from typing import List

from src.contexts.data_quality_triage.domain.entities.triage_case import TriageCase
from src.contexts.data_quality_triage.domain.value_objects.validation_result import ValidationResult

@dataclass
class ActivityPolicy:
    required_document_codes: list[str]

    def evaluate(self, case):
        present = {
            doc["document_code"]
            for doc in case.canonical_data
        }

        missing = [
            code for code in self.required_document_codes
            if code not in present
        ]

        return ValidationResult(
            is_valid=len(missing) == 0,
            missing_documents=missing,
            issues=[]
        )