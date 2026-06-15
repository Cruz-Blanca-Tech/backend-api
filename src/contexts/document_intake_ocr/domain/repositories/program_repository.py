# src/contexts/document_intake_ocr/domain/repositories/program_repository.py
from abc import ABC, abstractmethod
from uuid import UUID
from typing import List, Optional
from src.contexts.document_intake_ocr.domain.entities.program import Program

class ProgramRepository(ABC):
    @abstractmethod
    async def get_by_id(self, program_id: UUID) -> Optional[Program]:
        pass

    @abstractmethod
    async def list_all(self) -> List[Program]:
        pass

    @abstractmethod
    async def save(self, program: Program) -> None:
        pass