from __future__ import annotations
from uuid import UUID as PyUUID, uuid4
from datetime import datetime
from typing import Optional, List
from sqlalchemy import Float, String, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.core.database import Base

class TriageCaseModel(Base):
    __tablename__ = "triage_cases"

    id: Mapped[PyUUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    batch_id: Mapped[PyUUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("extraction_batches.id"), nullable=False)
    activity_type: Mapped[str] = mapped_column(String(50), nullable=False, server_default="UNKNOWN")
    dni_reference: Mapped[str] = mapped_column(String(20), nullable=False)

    documents_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False)
    document_ids: Mapped[dict] = mapped_column(JSONB, nullable=False)
    confidence_scores: Mapped[dict] = mapped_column(JSONB, nullable=False)
    corrected_data: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    status: Mapped[str] = mapped_column(String(50), nullable=False)
    verdict: Mapped[str] = mapped_column(String(50), nullable=False)
    discrepancies: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)

    rejection_reason: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    resolved_by: Mapped[Optional[PyUUID]] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    audit_logs: Mapped[List["TriageAuditLogModel"]] = relationship(  # type: ignore
        "TriageAuditLogModel",
        back_populates="triage_case",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
