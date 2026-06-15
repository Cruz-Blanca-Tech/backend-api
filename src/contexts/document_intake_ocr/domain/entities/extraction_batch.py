from dataclasses import dataclass, field
from uuid import UUID, uuid4
from typing import List, Optional
from datetime import datetime
from enum import Enum

from src.contexts.document_intake_ocr.domain.entities.document import DocumentItem, DocumentStatus
from src.contexts.document_intake_ocr.domain.entities.dossier import Dossier
from src.core.validators.exceptions import DomainValidationError

class BatchStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

@dataclass
class ExtractionBatch:
    """
    Agregado Raíz. Gestiona la integridad del proceso de ingesta: 
    expedientes válidos y documentos rechazados por filtros.
    """
    id: UUID
    activity_id: UUID
    created_by: UUID
    status: BatchStatus = BatchStatus.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    # Listas protegidas para evitar manipulación externa directa
    _dossiers: List[Dossier] = field(default_factory=list)
    _rejected_documents: List[DocumentItem] = field(default_factory=list)

    @property
    def dossiers(self) -> List[Dossier]:
        return list(self._dossiers)

    @property
    def rejected_documents(self) -> List[DocumentItem]:
        return list(self._rejected_documents)

    def add_dossier(self, dossier: Dossier) -> None:
        """Agrega un expediente validado al lote."""
        if not isinstance(dossier, Dossier):
            raise DomainValidationError("Solo se pueden agregar instancias de Dossier.")
        self._dossiers.append(dossier)

    def add_rejected_document(self, document: DocumentItem) -> None:
        """
        Registra un documento fallido. Protege el invariante de estado.
        """
        if document.status != DocumentStatus.FAILED:
            raise DomainValidationError(
                f"No se puede registrar el documento '{document.file_name}' "
                f"como rechazado porque su estado es '{document.status}'."
            )
        self._rejected_documents.append(document)

    def get_all_documents(self) -> List[DocumentItem]:
        """
        Aplanamiento de documentos para el motor de OCR asíncrono.
        Retorna tanto los documentos de los dossiers como los rechazados.
        """
        all_docs = [doc for dossier in self._dossiers for doc in dossier.documents]
        all_docs.extend(self._rejected_documents)
        return all_docs