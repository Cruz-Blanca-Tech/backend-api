from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from src.contexts.document_intake_ocr.infrastructure.persistence.model.document_item_model import DocumentItemModel
from src.contexts.document_intake_ocr.infrastructure.persistence.model.extraction_batch_model import ExtractionBatchModel
from src.contexts.document_intake_ocr.infrastructure.persistence.model.activity_model import ActivityModel
from src.contexts.document_intake_ocr.infrastructure.persistence.model.activity_requirement_model import ActivityRequirementModel
from src.contexts.document_intake_ocr.application.schemas.document_query_schema import (
    DocumentDossierItemResponse, 
    GetDocumentsByDossierResponse,
    PendingDocumentResponse
)

class GetDocumentsByDossierUseCase:
    """
    Query Use Case para obtener la lista de documentos asociados a un expediente (DNI dentro de un Lote).
    Retorna datos mínimos necesarios para el frontend (ID, código, nombre y URL de almacenamiento).
    También calcula los documentos pendientes de subir.
    """
    def __init__(self, session: AsyncSession):
        self.session = session

    async def execute(self, batch_id: UUID, dni_reference: str) -> GetDocumentsByDossierResponse:
        # Obtener documentos existentes
        stmt_docs = select(DocumentItemModel).where(
            DocumentItemModel.batch_id == batch_id,
            DocumentItemModel.dni_reference == dni_reference
        )
        result_docs = await self.session.execute(stmt_docs)
        models = result_docs.scalars().all()
        
        # Obtener el batch para extraer el tipo de actividad y sus requisitos
        stmt_batch = select(ExtractionBatchModel).options(
            joinedload(ExtractionBatchModel.activity)
            .joinedload(ActivityModel.requirements)
            .joinedload(ActivityRequirementModel.document_config)
        ).where(
            ExtractionBatchModel.id == batch_id
        )
        result_batch = await self.session.execute(stmt_batch)
        batch = result_batch.scalars().first()
        
        # Mapear a DTO
        items = [
            DocumentDossierItemResponse(
                id=m.id,
                code=m.code,
                file_name=m.file_name,
                source_id=m.source_id
            ) for m in models
        ]
        
        # Calcular pendientes desde la configuración de la actividad
        pending_docs = []
        if batch and batch.activity:
            required_configs = {
                req.document_config.code: req.document_config.name
                for req in batch.activity.requirements 
                if req.is_required and req.document_config
            }
            found_codes = {m.code for m in models if m.code}
            
            missing_codes = set(required_configs.keys()) - found_codes
            # Ordenar alfabéticamente para una respuesta determinista
            missing_codes_sorted = sorted(list(missing_codes))
            
            pending_docs = [
                PendingDocumentResponse(code=code, name=required_configs[code])
                for code in missing_codes_sorted
            ]
            
        return GetDocumentsByDossierResponse(documents=items, pending_documents=pending_docs)
