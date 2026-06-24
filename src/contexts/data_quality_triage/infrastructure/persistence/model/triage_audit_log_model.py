from __future__ import annotations
from uuid import UUID as PyUUID, uuid4
from datetime import datetime
from typing import Optional
from sqlalchemy import String, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.core.database import Base

class TriageAuditLogModel(Base):
    __tablename__ = "triage_audit_log"

    id: Mapped[PyUUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    triage_case_id: Mapped[PyUUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("triage_cases.id"), nullable=False)

    action: Mapped[str] = mapped_column(String(50), nullable=False)
    performed_by: Mapped[PyUUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)

    previous_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    new_status: Mapped[str] = mapped_column(String(50), nullable=False)
    details: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    triage_case: Mapped["TriageCaseModel"] = relationship("TriageCaseModel", back_populates="audit_logs")
