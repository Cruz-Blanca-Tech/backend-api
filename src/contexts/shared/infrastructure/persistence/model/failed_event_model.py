from __future__ import annotations
from uuid import UUID as PyUUID, uuid4
from datetime import datetime
from typing import Optional
from sqlalchemy import String, DateTime, Text, Integer, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column
from src.core.database import Base

class FailedEventModel(Base):
    __tablename__ = "failed_events"

    id: Mapped[PyUUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    event_name: Mapped[str] = mapped_column(String(100), nullable=False)
    aggregate_id: Mapped[Optional[PyUUID]] = mapped_column(PG_UUID(as_uuid=True), nullable=True, index=True)
    handler_name: Mapped[str] = mapped_column(String(100), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    error_message: Mapped[str] = mapped_column(String(1000), nullable=False)
    stack_trace: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="FAILED", index=True)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    last_retry_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
