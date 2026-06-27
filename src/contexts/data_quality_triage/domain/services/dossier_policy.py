from abc import ABC, abstractmethod
from typing import Dict, Any, List, Tuple

class DossierPolicy(ABC):
    """
    Abstracción base para las Políticas de Dossier.
    Se ejecuta de forma aislada en la Fase 1: Creación del Dossier.
    Se encarga de evaluar las inconsistencias cruzadas entre los distintos documentos extraídos.
    """

    @abstractmethod
    def evaluate(self, raw_docs: Dict[str, Any]) -> List[str]:
        """
        Evalúa el conjunto de documentos en bruto (instancias Pydantic).
        Retorna:
            - List[str]: Lista de errores encontrados. Si la lista está vacía, no hay inconsistencias cruzadas.
        """
        pass
