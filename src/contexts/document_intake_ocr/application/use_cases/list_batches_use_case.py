import logging
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from src.contexts.document_intake_ocr.infrastructure.persistence.model.extraction_batch_model import ExtractionBatchModel
from src.contexts.document_intake_ocr.infrastructure.persistence.model.activity_model import ActivityModel
from src.contexts.document_intake_ocr.domain.ports.triage_service import TriageServicePort
from src.contexts.document_intake_ocr.domain.entities.document import DocumentStatus
from src.contexts.document_intake_ocr.application.schemas.batch_schema import ListBatchesRequest
from uuid import UUID
from typing import Optional

logger = logging.getLogger(__name__)

class ListBatchesUseCase:
    def __init__(self, session: AsyncSession, triage_service: TriageServicePort):
        self.session = session
        self.triage_service = triage_service

    async def execute(self, request: ListBatchesRequest) -> dict:
        stmt = select(ExtractionBatchModel).options(
            joinedload(ExtractionBatchModel.activity).joinedload(ActivityModel.program)
        )
        
        if request.activity_id:
            stmt = stmt.where(ExtractionBatchModel.activity_id == request.activity_id)
        if request.program_id:
            stmt = stmt.join(ActivityModel).where(ActivityModel.program_id == request.program_id)
        if request.status:
            stmt = stmt.where(ExtractionBatchModel.status == request.status)
            
        stmt = stmt.order_by(ExtractionBatchModel.created_at.desc()).offset(request.skip).limit(request.limit)
        result = await self.session.execute(stmt)
        batches = result.scalars().all()
        
        batch_ids = [b.id for b in batches]
        triage_summaries = await self.triage_service.get_triage_summaries(batch_ids) if batch_ids else {}
        
        return {
            "total": len(batches),
            "batches": [
                {
                    "id": str(b.id),
                    "activity_id": str(b.activity_id),
                    "status": b.status,
                    "created_at": b.created_at.isoformat() if b.created_at else None,
                    "documents_failed_count": sum(1 for d in getattr(b, 'documents', []) if d.status == DocumentStatus.FAILED),
                    "documents_approved_count": sum(1 for d in getattr(b, 'documents', []) if d.status == DocumentStatus.APPROVED),
                    "description": b.description,
                    "activity_name": b.activity.name if getattr(b, 'activity', None) else None,
                    "program_name": b.activity.program.name if getattr(b, 'activity', None) and getattr(b.activity, 'program', None) else None,
                    "triage_summary": triage_summaries.get(b.id, {
                        "total_cases": 0,
                        "verdicts": {}
                    })
                }
                for b in batches
            ]
        }
