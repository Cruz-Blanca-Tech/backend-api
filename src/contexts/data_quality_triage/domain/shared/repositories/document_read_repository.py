# bc3/domain/ports/document_read_repository.py

from typing import List, Protocol
from uuid import UUID

from src.contexts.data_quality_triage.domain.shared.dtos.document_dto import DocumentDTO



class DocumentReadRepository(Protocol):

    async def get_by_dni(
        self,
        dni_reference: str
    ) -> List[DocumentDTO]:
        ...