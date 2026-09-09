import json
import logging
import traceback
from uuid import UUID, uuid4
from typing import Any, Optional, Dict
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from src.contexts.shared.infrastructure.persistence.model.failed_event_model import FailedEventModel

logger = logging.getLogger(__name__)

class DeadLetterService:
    @staticmethod
    def _json_serializable(obj: Any) -> Any:
        if isinstance(obj, UUID):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        if hasattr(obj, "__dict__"):
            return {k: DeadLetterService._json_serializable(v) for k, v in obj.__dict__.items()}
        if isinstance(obj, dict):
            return {str(k): DeadLetterService._json_serializable(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple, set)):
            return [DeadLetterService._json_serializable(x) for x in obj]
        return obj

    @classmethod
    async def record_failure(
        cls,
        session: AsyncSession,
        event: Any,
        handler_name: str,
        error: Exception,
        aggregate_id: Optional[UUID] = None,
        retry_count: int = 0
    ) -> FailedEventModel:
        event_name = type(event).__name__
        
        if aggregate_id is None:
            if hasattr(event, "triage_case_id"):
                aggregate_id = event.triage_case_id
            elif hasattr(event, "batch_id"):
                aggregate_id = event.batch_id

        payload = cls._json_serializable(event)
        if not isinstance(payload, dict):
            payload = {"data": payload}

        error_message = str(error)[:1000] if error else "Error desconocido"
        stack = traceback.format_exc()

        # Check if an existing failed event exists for this aggregate and handler to increment retry_count
        stmt = (
            select(FailedEventModel)
            .where(
                FailedEventModel.aggregate_id == aggregate_id,
                FailedEventModel.handler_name == handler_name,
                FailedEventModel.status == "FAILED"
            )
            .order_by(FailedEventModel.created_at.desc())
        )
        res = await session.execute(stmt)
        existing = res.scalars().first()

        if existing:
            existing.retry_count += 1
            existing.error_message = error_message
            existing.stack_trace = stack
            existing.last_retry_at = datetime.now()
            logger.warning(
                f"[DeadLetterService] Actualizado evento fallido existente {existing.id} "
                f"({event_name}) para agregado {aggregate_id}. Intentos: {existing.retry_count}."
            )
            return existing

        failed_event = FailedEventModel(
            id=uuid4(),
            event_name=event_name,
            aggregate_id=aggregate_id,
            handler_name=handler_name,
            payload=payload,
            error_message=error_message,
            stack_trace=stack,
            status="FAILED",
            retry_count=retry_count
        )
        session.add(failed_event)
        logger.warning(
            f"[DeadLetterService] Registrado nuevo evento fallido {failed_event.id} "
            f"({event_name}) en Dead Letter Queue para agregado {aggregate_id}."
        )
        return failed_event

    @classmethod
    async def mark_resolved(
        cls,
        session: AsyncSession,
        aggregate_id: UUID,
        handler_name: Optional[str] = None
    ) -> int:
        stmt = (
            update(FailedEventModel)
            .where(
                FailedEventModel.aggregate_id == aggregate_id,
                FailedEventModel.status == "FAILED"
            )
            .values(status="RESOLVED", last_retry_at=datetime.now())
        )
        if handler_name:
            stmt = stmt.where(FailedEventModel.handler_name == handler_name)

        res = await session.execute(stmt)
        return res.rowcount
