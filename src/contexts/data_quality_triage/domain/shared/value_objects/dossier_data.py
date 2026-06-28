from abc import ABC, abstractmethod
from typing import Dict, Any, List, Tuple

class DossierData(ABC):
    """
    Abstracción de dominio base para cualquier expediente.
    Representa la estructura unificada de datos tras extraer información de múltiples documentos.
    """

    @abstractmethod
    def validate_completeness(self) -> Tuple[bool, List[str]]:
        """
        Ejecuta la validación final (Fase 2) de reglas de completitud.
        Retorna:
            - bool: Si el dossier es válido.
            - List[str]: Lista de errores encontrados.
        """
        pass
