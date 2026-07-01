import logging
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from fastapi import HTTPException
from src.contexts.document_intake_ocr.infrastructure.persistence.model.extraction_batch_model import ExtractionBatchModel
from src.contexts.document_intake_ocr.infrastructure.persistence.model.activity_model import ActivityModel
from src.contexts.document_intake_ocr.domain.ports.triage_service import TriageServicePort
from src.contexts.document_intake_ocr.domain.entities.document import DocumentStatus
from src.contexts.document_intake_ocr.application.schemas.batch_schema import BatchItemSchema
from uuid import UUID

logger = logging.getLogger(__name__)

class GetBatchByIdUseCase:
    def __init__(self, session: AsyncSession, triage_service: TriageServicePort):
        self.session = session
        self.triage_service = triage_service

    async def execute(self, batch_id: UUID) -> BatchItemSchema:
        stmt = (
            select(ExtractionBatchModel)
            .options(joinedload(ExtractionBatchModel.activity).joinedload(ActivityModel.program))
            .where(ExtractionBatchModel.id == batch_id)
        )
        
        result = await self.session.execute(stmt)
        b = result.scalars().first()
        
        if not b:
            raise HTTPException(status_code=404, detail="Batch not found")
        
        triage_summaries = await self.triage_service.get_triage_summaries([b.id])
        
        return BatchItemSchema(
            id=b.id,
            activity_id=b.activity_id,
            status=b.status,
            created_at=b.created_at.isoformat() if b.created_at else None,
            documents_failed_count=sum(1 for d in getattr(b, 'documents', []) if d.status == DocumentStatus.FAILED),
            documents_approved_count=sum(1 for d in getattr(b, 'documents', []) if d.status == DocumentStatus.APPROVED),
            description=b.description,
            activity_name=b.activity.name if getattr(b, 'activity', None) else None,
            program_name=b.activity.program.name if getattr(b, 'activity', None) and getattr(b.activity, 'program', None) else None,
            triage_summary=triage_summaries.get(b.id, {
                "total_cases": 0,
                "verdicts": {}
            })
        )
