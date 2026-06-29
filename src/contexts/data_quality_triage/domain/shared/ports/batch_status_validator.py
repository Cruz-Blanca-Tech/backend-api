from abc import ABC, abstractmethod
from uuid import UUID

class BatchStatusValidatorPort(ABC):
    @abstractmethod
    async def is_batch_ready_for_triage(self, batch_id: UUID) -> bool:
        """
        Retorna True si el lote en el OCR ha finalizado su procesamiento y está
        listo para ser triajado (estado != PROCESSING).
        """
        pass
