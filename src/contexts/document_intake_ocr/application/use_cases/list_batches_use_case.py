import logging
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.contexts.document_intake_ocr.infrastructure.persistence.model.extraction_batch_model import ExtractionBatchModel

logger = logging.getLogger(__name__)

class ListBatchesUseCase:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def execute(self, skip: int = 0, limit: int = 100) -> dict:
        stmt = select(ExtractionBatchModel).order_by(ExtractionBatchModel.created_at.desc()).offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        batches = result.scalars().all()
        
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
                }
                for b in batches
            ]
        }
