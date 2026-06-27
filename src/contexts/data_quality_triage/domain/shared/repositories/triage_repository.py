from abc import ABC, abstractmethod
from typing import Optional, List, Tuple
from uuid import UUID
from src.contexts.data_quality_triage.domain.shared.entities.triage_case import TriageCase

class TriageRepository(ABC):
    @abstractmethod
    async def save(self, case: TriageCase) -> None: pass
    @abstractmethod
    async def get_by_id(self, case_id: UUID) -> Optional[TriageCase]: pass
    @abstractmethod
    async def get_by_dossier(self, batch_id: UUID, dni_reference: str) -> Optional[TriageCase]: pass
    @abstractmethod
    async def list_pending(self, skip: int = 0, limit: int = 20) -> Tuple[List[TriageCase], int]: pass
    @abstractmethod
    async def list_by_batch_id(self, batch_id: UUID, skip: int = 0, limit: int = 20) -> Tuple[List[TriageCase], int]: pass
    @abstractmethod
    async def get_all_by_batch_id(self, batch_id: UUID) -> List[TriageCase]: pass
    @abstractmethod
    async def bulk_save(self, cases: List[TriageCase]) -> None: pass
