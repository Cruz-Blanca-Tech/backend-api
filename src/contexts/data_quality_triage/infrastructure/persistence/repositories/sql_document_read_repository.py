from typing import List
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.contexts.data_quality_triage.domain.shared.dtos.document_dto import DocumentDTO
from src.contexts.data_quality_triage.domain.shared.repositories.document_read_repository import DocumentReadRepository
from src.contexts.document_intake_ocr.infrastructure.persistence.model.document_item_model import DocumentItemModel


class SqlDocumentReadRepository(DocumentReadRepository):

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_dni(
        self,
        dni_reference: str
    ) -> List[DocumentDTO]:

        stmt = select(DocumentItemModel).where(
            DocumentItemModel.dni_reference == dni_reference
        )
        result = await self.session.execute(stmt)
        rows = result.scalars().all()

        return [
            DocumentDTO(
                id=r.id,
                file_name=r.file_name,
                document_code=r.code,
                extracted_data=r.extracted_data or {},
                confidence_score=r.confidence_score
            )
            for r in rows
        ]