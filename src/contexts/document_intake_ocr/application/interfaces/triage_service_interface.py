# src/contexts/document_intake_ocr/application/interfaces/triage_service_interface.py
from abc import ABC, abstractmethod
from uuid import UUID

class TriageService(ABC):
    @abstractmethod
    async def process_triage_for_dossier(self, batch_id: UUID, dni: str) -> None:
        """
        Notifica al contexto de triaje que un dossier está listo para validación.
        """
        pass