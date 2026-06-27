# src/contexts/data_quality_triage/domain/ports/policy_repository.py
from abc import ABC, abstractmethod
from uuid import UUID
from typing import Optional
from src.contexts.data_quality_triage.domain.entities.triage_policy import TriagePolicy

class PolicyRepository(ABC):
    """
    Puerto (Interface) que define las operaciones de persistencia 
    para las políticas de triaje locales.
    """
    @abstractmethod
    async def save(self, policy: TriagePolicy) -> None:
        """Guarda o actualiza una política en la réplica local."""
        pass

    @abstractmethod
    async def get_by_activity_id(self, activity_id: UUID) -> Optional[TriagePolicy]:
        """Recupera la política asociada a un programa."""
        pass