from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.contexts.document_intake_ocr.infrastructure.persistence.model.document_item_model import DocumentItemModel
from src.contexts.document_intake_ocr.infrastructure.persistence.model.extraction_batch_model import ExtractionBatchModel
from src.contexts.document_intake_ocr.infrastructure.persistence.model.activity_model import ActivityModel
from src.contexts.document_intake_ocr.infrastructure.persistence.model.activity_requirement_model import ActivityRequirementModel
from src.contexts.document_intake_ocr.infrastructure.persistence.model.document_type_config import DocumentTypeConfigModel
from src.contexts.document_intake_ocr.application.schemas.document_query_schema import (
    DocumentDossierItemResponse, GetDocumentsByDossierResponse, PendingDocumentItemResponse
)

class GetDocumentsByDossierUseCase:
    """
    Query Use Case para obtener la lista de documentos asociados a un expediente (DNI dentro de un Lote).
    Retorna datos mínimos necesarios para el frontend (ID, código, nombre y URL de almacenamiento),
    además de los documentos requeridos faltantes (pending_documents).
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

        # Calcular documentos pendientes contrastando contra activity_requirements
        pending_documents = []
        batch_stmt = select(ExtractionBatchModel).where(ExtractionBatchModel.id == batch_id)
        batch_res = await self.session.execute(batch_stmt)
        batch = batch_res.scalar_one_or_none()

        if batch and batch.activity_id:
            req_stmt = (
                select(ActivityRequirementModel, DocumentTypeConfigModel)
                .join(DocumentTypeConfigModel, ActivityRequirementModel.document_type_config_id == DocumentTypeConfigModel.id)
                .where(
                    ActivityRequirementModel.activity_id == batch.activity_id,
                    ActivityRequirementModel.is_required == True
                )
            )
            req_res = await self.session.execute(req_stmt)
            requirements = req_res.all()

            uploaded_codes = {m.code for m in models if m.code}
            for req, config in requirements:
                if config.code not in uploaded_codes:
                    pending_documents.append(
                        PendingDocumentItemResponse(
                            code=config.code,
                            name=config.name
                        )
                    )

        return GetDocumentsByDossierResponse(
            documents=items,
            pending_documents=pending_documents
        )
