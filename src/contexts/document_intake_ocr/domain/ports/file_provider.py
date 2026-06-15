from abc import ABC, abstractmethod
from typing import List
from src.contexts.document_intake_ocr.domain.value_objects.file_item import FileItem
from src.contexts.document_intake_ocr.domain.value_objects.raw_file import FileStream

class FileProviderPort(ABC):
    """
    Puerto para la Ingesta: Responsable de extraer el 'FileStream' 
    desde la fuente externa original.
    """

    @abstractmethod
    def list_files_in_folder(self, folder_id: str) -> List[FileItem]:
        """
        Descubre los metadatos de los archivos en la nube.
        Ideal para el BatchProcessor (para agrupar por DNI).
        """
        pass
    
    @abstractmethod
    def get_file(self, file_id: str) -> FileStream: 
        """
        Ahora retorna un FileStream, que encapsula el stream, 
        el nombre, el tipo MIME y la extensión.
        """
        pass