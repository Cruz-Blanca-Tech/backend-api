# bc3/infrastructure/repositories/sql_document_read_repository.py

from typing import List
from uuid import UUID

from sqlalchemy.orm import Session

from src.contexts.data_quality_triage.domain.dtos.document_dto import DocumentDTO
from src.contexts.data_quality_triage.domain.repositories.document_read_repository import DocumentReadRepository
from src.contexts.shared.infrastructure.persistence.models.document_item_model import DocumentItemModel


class SqlDocumentReadRepository(DocumentReadRepository):

    def __init__(self, session: Session):
        self.session = session

    async def get_by_context(
        self,
        batch_id: UUID,
        activity_id: UUID,
        dni_reference: str
    ) -> List[DocumentDTO]:

        rows = (
            self.session.query(DocumentItemModel)
            .filter(
                DocumentItemModel.batch_id == batch_id,
                DocumentItemModel.dni_reference == dni_reference
            )
            .all()
        )

        return [
            DocumentDTO(
                id=r.id,
                file_name=r.file_name,
                document_code=r.code,
                extracted_data=r.raw_data.data or {},
                confidence_score=r.confidence_score
            )
            for r in rows
        ]