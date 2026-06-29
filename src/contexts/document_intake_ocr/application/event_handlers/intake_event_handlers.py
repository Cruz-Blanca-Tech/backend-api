import logging
from uuid import UUID
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.database import async_session_maker
from src.contexts.document_intake_ocr.infrastructure.persistence.model.document_item_model import DocumentItemModel
from src.contexts.document_intake_ocr.infrastructure.persistence.model.extraction_batch_model import ExtractionBatchModel
from src.contexts.shared.events.batch_triage_completed_event import BatchTriageCompletedEvent

logger = logging.getLogger(__name__)

async def handle_dossier_approved(event) -> None:
    logger.info(f"[Intake Event Handler] Expediente aprobado - Actualizando {len(event.document_ids)} documentos a APPROVED")
    async with async_session_maker() as session:
        for doc_id in event.document_ids:
            stmt = update(DocumentItemModel).where(DocumentItemModel.id == doc_id).values(status="APPROVED")
            await session.execute(stmt)
        await session.commit()

async def handle_dossier_rejected(event) -> None:
    logger.info(f"[Intake Event Handler] Expediente rechazado - Actualizando {len(event.document_ids)} documentos a FAILED")
    async with async_session_maker() as session:
        for doc_id in event.document_ids:
            stmt = update(DocumentItemModel).where(DocumentItemModel.id == doc_id).values(status="FAILED", failure_reason=f"Rechazado en triaje: {event.reason}")
            await session.execute(stmt)
        await session.commit()

async def handle_batch_rejected(event) -> None:
    logger.info(f"[Intake Event Handler] Lote {event.batch_id} rechazado masivamente - Actualizando {len(event.document_ids)} documentos a FAILED")
    async with async_session_maker() as session:
        for doc_id in event.document_ids:
            stmt = update(DocumentItemModel).where(DocumentItemModel.id == doc_id).values(status="FAILED", failure_reason=f"Lote rechazado masivamente: {event.reason}")
            stmt = update(DocumentItemModel).where(DocumentItemModel.id == doc_id).values(status="FAILED", failure_reason=f"Lote rechazado masivamente: {event.reason}")
            await session.execute(stmt)
        await session.commit()

async def handle_batch_triage_completed(event: BatchTriageCompletedEvent) -> None:
    logger.info(f"[Intake Event Handler] Lote de triaje completado - Actualizando batch {event.batch_id} a CORRECTED")
    async with async_session_maker() as session:
        stmt = (
            update(ExtractionBatchModel)
            .where(ExtractionBatchModel.id == event.batch_id)
            .values(status="CORRECTED")
        )
        await session.execute(stmt)
        await session.commit()
