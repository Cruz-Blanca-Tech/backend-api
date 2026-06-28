from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.contexts.document_intake_ocr.infrastructure.persistence.model.document_item_model import DocumentItemModel
from src.contexts.document_intake_ocr.application.schemas.document_query_schema import DocumentDossierItemResponse, GetDocumentsByDossierResponse

class GetDocumentsByDossierUseCase:
    """
    Query Use Case para obtener la lista de documentos asociados a un expediente (DNI dentro de un Lote).
    Retorna datos mínimos necesarios para el frontend (ID, código, nombre y URL de almacenamiento).
    """
    def __init__(self, session: AsyncSession):
        self.session = session

    async def execute(self, batch_id: UUID, dni_reference: str) -> GetDocumentsByDossierResponse:
        stmt = select(DocumentItemModel).where(
            DocumentItemModel.batch_id == batch_id,
            DocumentItemModel.dni_reference == dni_reference
        )
        result = await self.session.execute(stmt)
        models = result.scalars().all()
        
        items = [
            DocumentDossierItemResponse(
                id=m.id,
                code=m.code,
                file_name=m.file_name,
                source_id=m.source_id
            ) for m in models
        ]
        return GetDocumentsByDossierResponse(documents=items)
