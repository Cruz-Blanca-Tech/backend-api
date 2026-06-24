from typing import List, Optional, Dict
from uuid import UUID
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from src.contexts.data_quality_triage.infrastructure.acl.intake_dtos import DocumentReadDTO
from src.contexts.document_intake_ocr.infrastructure.persistence.model.document_item_model import DocumentItemModel
from src.contexts.document_intake_ocr.infrastructure.persistence.model.extraction_batch_model import ExtractionBatchModel
from src.contexts.document_intake_ocr.infrastructure.persistence.model.activity_requirement_model import ActivityRequirementModel
from src.contexts.document_intake_ocr.infrastructure.persistence.model.document_type_config import DocumentTypeConfigModel

class IntakeACL:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_documents_ready_for_review(self, batch_id: UUID) -> List[DocumentReadDTO]:
        stmt = select(DocumentItemModel).where(
            and_(
                DocumentItemModel.batch_id == batch_id,
                DocumentItemModel.status == "READY_FOR_REVIEW",
            )
        )
        result = await self.session.execute(stmt)
        models = result.scalars().all()
        return [
            DocumentReadDTO(
                id=m.id,
                batch_id=m.batch_id,
                document_code=m.code or "UNKNOWN",
                file_name=m.file_name,
                dni_reference=m.dni_reference or "",
                extracted_data=m.extracted_data or {},
                confidence_score=m.confidence_score,
            )
            for m in models
        ]

    async def get_activity_id_for_batch(self, batch_id: UUID) -> Optional[UUID]:
        stmt = select(ExtractionBatchModel.activity_id).where(ExtractionBatchModel.id == batch_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all_thresholds_for_activity(self, activity_id: UUID) -> Dict[str, float]:
        stmt = (
            select(DocumentTypeConfigModel.code, ActivityRequirementModel.confidence_threshold)
            .join(DocumentTypeConfigModel, ActivityRequirementModel.document_type_config_id == DocumentTypeConfigModel.id)
            .where(ActivityRequirementModel.activity_id == activity_id)
        )
        result = await self.session.execute(stmt)
        rows = result.all()
        return {code: threshold for code, threshold in rows}
