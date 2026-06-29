import logging
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func
from src.contexts.document_intake_ocr.infrastructure.persistence.model.extraction_batch_model import ExtractionBatchModel
from src.contexts.document_intake_ocr.infrastructure.persistence.model.activity_model import ActivityModel
from src.contexts.document_intake_ocr.domain.entities.extraction_batch import BatchStatus
from uuid import UUID
from typing import Optional

logger = logging.getLogger(__name__)

class GetBatchesSummaryUseCase:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def execute(
        self,
        program_id: Optional[UUID] = None,
        activity_id: Optional[UUID] = None
    ) -> dict:
        stmt = select(ExtractionBatchModel.status, func.count(ExtractionBatchModel.id).label("count"))
        
        if activity_id:
            stmt = stmt.where(ExtractionBatchModel.activity_id == activity_id)
        if program_id:
            stmt = stmt.join(ActivityModel).where(ActivityModel.program_id == program_id)
            
        stmt = stmt.group_by(ExtractionBatchModel.status)
        result = await self.session.execute(stmt)
        rows = result.all()
        
        # Initialize counts for all known statuses to 0
        statuses_summary = {s.value: 0 for s in BatchStatus}
        total_batches = 0
        
        for status_val, count in rows:
            statuses_summary[status_val] = count
            total_batches += count
            
        return {
            "total_batches": total_batches,
            "statuses": statuses_summary
        }
