# src/contexts/document_intake_ocr/domain/value_objects/sub_batch_validation_report.py

from dataclasses import dataclass
from typing import List

from src.contexts.document_intake_ocr.domain.value_objects.document_code import DocumentTypeCode

@dataclass(frozen=True)
class SubBatchValidationReport:
    """
    Value Object que encapsula el resultado de la validación estructural.
    Es inmutable, garantizando que el diagnóstico no sea alterado una vez generado.
    """
    is_valid: bool
    missing_codes: List[DocumentTypeCode]
    extra_codes: List[DocumentTypeCode]

    @property
    def has_errors(self) -> bool:
        return not self.is_valid    