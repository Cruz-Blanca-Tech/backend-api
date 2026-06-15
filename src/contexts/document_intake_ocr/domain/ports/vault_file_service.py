from abc import ABC, abstractmethod

class VaultFileService(ABC):
    """
    Puerto para la Custodia: Responsable de archivar el documento 
    en el repositorio final y protegido de la ONG.
    """
    @abstractmethod
    def archive(self, file_id: str, content: bytes) -> str: 
        """Retorna el nuevo ID o enlace del archivo archivado."""
        pass