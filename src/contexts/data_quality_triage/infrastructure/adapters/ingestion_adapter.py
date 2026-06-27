# src/contexts/data_quality_triage/infrastructure/adapters/ingestion_adapter.py

from typing import List
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.contexts.data_quality_triage.domain.dtos.document_dto import DocumentDTO
from src.contexts.data_quality_triage.domain.ports.document_provider import DocumentProvider
from src.contexts.shared.infrastructure.persistence.models.document_item_model import DocumentItemModel


class IngestionAdapter(DocumentProvider):
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_documents_by_batch_and_dni(self, batch_id: UUID, dni: str) -> List[DocumentDTO]:
        """
        Consulta precisa: filtra documentos por Lote y por DNI.
        """
        query = (
            select(DocumentItemModel)
            .where(
                DocumentItemModel.batch_id == batch_id,
                DocumentItemModel.dni_reference == dni
            )
        )
        result = await self.db.execute(query)
        
        return [
            DocumentDTO(
                id=doc.id, 
                code=doc.code, 
                status=doc.status,
                extracted_data=doc.extracted_data
            ) 
            for doc in result.scalars().all()
        ]