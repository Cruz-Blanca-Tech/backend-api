# src/contexts/document_intake_ocr/domain/entities/dossier.py
import uuid
from typing import List
from enum import Enum
from src.contexts.document_intake_ocr.domain.entities.activity import ActivityRequirement
from src.contexts.document_intake_ocr.domain.entities.document import DocumentItem
from src.contexts.document_intake_ocr.domain.value_objects.dni import DNI

class DossierStatus(str, Enum):
    PENDING_VALIDATION = "PENDING_VALIDATION"
    COMPLETE = "COMPLETE"
    INCOMPLETE = "INCOMPLETE"

class Dossier:
    def __init__(self, dni: DNI, activity_id: uuid.UUID, batch_id: uuid.UUID):
        self.dni = dni
        self.activity_id = activity_id
        self.batch_id = batch_id
        self.documents: List[DocumentItem] = []
        self.status = DossierStatus.PENDING_VALIDATION
        self.errors: List[str] = []

    def add_document(self, doc: DocumentItem) -> None:
        self.documents.append(doc)

    def is_complete(self, requirements: List[ActivityRequirement]) -> bool:
        present_codes = {doc.document_code for doc in self.documents if doc.document_code}
        return all(not req.is_required or req.document_config.code in present_codes for req in requirements)

    def update_status(self, requirements: List[ActivityRequirement]) -> None:
        missing = [req.document_config.code.code for req in requirements if req.is_required and req.document_config.code not in {d.document_code for d in self.documents}]
        if not missing:
            self.status = DossierStatus.COMPLETE
            self.errors = []
        else:
            self.status = DossierStatus.INCOMPLETE
            self.errors = [f"Faltan documentos: {', '.join(missing)}"]