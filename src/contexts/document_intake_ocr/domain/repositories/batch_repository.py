from abc import ABC, abstractmethod
from typing import Optional
import uuid
from src.contexts.document_intake_ocr.domain.entities.extraction_batch import ExtractionBatch

class BatchRepository(ABC):
    """
    Puerto (Interfaz) del repositorio para la raíz de agregado ExtractionBatch.
    Cualquier operación sobre documentos individuales debe pasar por aquí.
    """

    @abstractmethod
    async def save(self, batch: ExtractionBatch) -> None:
        """Inserta o actualiza un Batch completo (incluyendo sus DocumentItems)"""
        pass

    @abstractmethod
    async def get_by_id(self, batch_id: uuid.UUID) -> Optional[ExtractionBatch]:
        """Obtiene un Batch y toda su colección de documentos internos"""
        pass

    # =========================================================
    # EL TRUCO SENIOR (Para tu Worker Asíncrono)
    # =========================================================
    @abstractmethod
    async def get_by_document_id(self, document_id: uuid.UUID) -> Optional[ExtractionBatch]:
        """
        Permite a Celery o al Webhook de Azure encontrar el Lote completo 
        sabiendo únicamente el ID de un documento específico que acaba de terminar.
        """
        pass