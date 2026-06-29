import logging
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.contexts.document_intake_ocr.infrastructure.persistence.model.extraction_batch_model import ExtractionBatchModel
from src.contexts.document_intake_ocr.domain.ports.triage_service import TriageServicePort
from uuid import UUID

logger = logging.getLogger(__name__)

class ListBatchesUseCase:
    def __init__(self, session: AsyncSession, triage_service: TriageServicePort):
        self.session = session
        self.triage_service = triage_service

    async def execute(self, skip: int = 0, limit: int = 100) -> dict:
        stmt = select(ExtractionBatchModel).order_by(ExtractionBatchModel.created_at.desc()).offset(skip).limit(limit)
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
                    "documents_failed_count": sum(1 for d in getattr(b, 'documents', []) if d.status == "FAILED"),
                    "documents_approved_count": sum(1 for d in getattr(b, 'documents', []) if d.status == "APPROVED"),
                    "description": b.description,
                    "triage_summary": triage_summaries.get(b.id, {
                        "total_cases": 0,
                        "verdicts": {}
                    })
                }
                for b in batches
            ]
        }
