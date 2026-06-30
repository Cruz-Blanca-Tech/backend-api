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

    @abstractmethod
    async def is_batch_rejectable(self, batch_id: UUID) -> bool:
        """
        Retorna True si el lote en el OCR está en un estado que permite ser rechazado
        (debe estar en estado PENDING).
        """
        pass

    @abstractmethod
    async def is_batch_completed(self, batch_id: UUID) -> bool:
        """
        Retorna True si el lote ya fue completado/triajado.
        """
        pass
