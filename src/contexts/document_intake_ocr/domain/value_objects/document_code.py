# src/contexts/document_intake_ocr/domain/value_objects/document_type_code.py
from dataclasses import dataclass
from uuid import uuid4

@dataclass(frozen=True)
class DocumentTypeCode:
    code: str

    def __post_init__(self):
        if not self.code or len(self.code) < 2:
            raise ValueError("El código de documento debe tener al menos 2 caracteres.")
            # src/contexts/document_intake_ocr/domain/entities/document_type.py