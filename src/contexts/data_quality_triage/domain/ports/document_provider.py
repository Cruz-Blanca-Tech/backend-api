# src/contexts/data_quality_triage/domain/ports/document_provider.py
from abc import ABC, abstractmethod
from typing import List
from uuid import UUID

from src.contexts.data_quality_triage.domain.dtos.document_dto import DocumentDTO

class DocumentProvider(ABC):
    @abstractmethod
    def get_documents_by_batch_and_dni(self, batch_id: UUID, dni: str) -> List[DocumentDTO]:
        """El dominio pide documentos, no sabe de dónde vienen."""
        pass