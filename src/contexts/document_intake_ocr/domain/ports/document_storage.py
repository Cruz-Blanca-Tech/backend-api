# src/contexts/document_intake_ocr/domain/ports/document_storage.py

from abc import ABC, abstractmethod
from src.contexts.document_intake_ocr.domain.value_objects.file_item import FileItem

class DocumentStorage(ABC):
    
    @abstractmethod
    async def ensure_batch_directory(self, activity_name: str, batch_id: str) -> str:
        pass
    
    @abstractmethod
    async def copy_to_custody(self, file_item: FileItem, target_folder_id: str, user_email: str) -> str:
        pass

    # ---- NUEVA CAPACIDAD ----
    @abstractmethod
    async def download_file(self, file_item: FileItem, user_email: str) -> bytes:
        """
        Descarga el contenido binario de un archivo desde Google Drive a la memoria RAM.
        """
        pass