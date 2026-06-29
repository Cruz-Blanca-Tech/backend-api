from abc import ABC, abstractmethod
from typing import List, Dict
from uuid import UUID

class TriageServicePort(ABC):
    @abstractmethod
    async def get_triage_summaries(self, batch_ids: List[UUID]) -> Dict[UUID, dict]:
        """
        Obtiene de forma masiva los resúmenes de triaje correspondientes a una lista de IDs de lotes.
        Retorna un diccionario mapeado por batch_id.
        """
        pass
