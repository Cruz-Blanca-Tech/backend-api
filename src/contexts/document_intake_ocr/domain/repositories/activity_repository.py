# src/contexts/document_intake_ocr/domain/repositories/activity_repository.py
from abc import ABC, abstractmethod
from typing import List
from uuid import UUID
from src.contexts.document_intake_ocr.domain.entities.activity import Activity

class ActivityRepository(ABC):
    @abstractmethod
    async def get_by_id(self, activity_id: UUID) -> Activity:
        """
        Debe retornar la Actividad con sus 'ActivityRequirements' cargados.
        """
        pass

    @abstractmethod
    async def get_by_program_id(self, program_id: UUID) -> List[Activity]: 
        """
        Debe retornar la Actividad con sus 'ActivityRequirements' cargados.
        """
        pass
    
    @abstractmethod
    async def list_all_active(self) -> List[Activity]: ... # <--- Nuevo método

    @abstractmethod
    async def save(self, activity: Activity) -> None:
        pass

