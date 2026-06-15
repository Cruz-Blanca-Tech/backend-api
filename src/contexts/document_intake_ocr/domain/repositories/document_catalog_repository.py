# src/contexts/document_intake_ocr/domain/repositories/document_catalog_repository.py
from abc import ABC, abstractmethod
from typing import List, Optional

from src.contexts.document_intake_ocr.domain.entities.document_type import DocumentTypeConfig

class DocumentCatalogRepository(ABC):
    @abstractmethod
    async def get_by_id(self, catalog_id: int) -> Optional[DocumentTypeConfig]:
        pass

    @abstractmethod
    async def get_all_active(self) -> List[DocumentTypeConfig]:
        """Vital para que el Frontend arme sus combos/dropdowns"""
        pass

    @abstractmethod
    async def save(self, document_config: DocumentTypeConfig) -> None:
        """Para cuando el Administrador registre nuevos modelos de IA"""
        pass
    
    @abstractmethod
    async def get_by_ids(self, ids: List[int]) -> List[DocumentTypeConfig]:
        """Para cuando se necesite validar que existen"""
        pass