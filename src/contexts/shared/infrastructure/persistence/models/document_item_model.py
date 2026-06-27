# src/contexts/document_intake_ocr/infrastructure/persistence/models/batch_model.py

from typing import Optional
from uuid import UUID as PyUUID
from datetime import datetime
from sqlalchemy import Float, ForeignKey, String, DateTime
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.contexts.document_intake_ocr.infrastructure.persistence.model.document_raw_data_model import DocumentRawDataModel
from src.core.database import Base  

class DocumentItemModel(Base):
    __tablename__ = "document_items"

    id = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    batch_id = mapped_column(PG_UUID(as_uuid=True), ForeignKey("extraction_batches.id"))

    source_id = mapped_column(String(500))
    custody_id = mapped_column(String(500))
    code = mapped_column(String(50))
    file_name = mapped_column(String(255))
    dni_reference = mapped_column(String(20))

    document_type_config_id = mapped_column(PG_UUID(as_uuid=True), ForeignKey("document_type_configs.id"))

    status = mapped_column(String(50))
    confidence_score = mapped_column(Float)
    failure_reason = mapped_column(String(500))
    processed_at = mapped_column(DateTime)

    # =========================
    # RELACIONES IMPORTANTES
    # =========================

    raw_data = relationship(
        DocumentRawDataModel,
        back_populates="document",
        uselist=False,
        cascade="all, delete-orphan"
    )

    canonical_data = relationship(
        "DocumentCanonicalDataModel",
        back_populates="document",
        uselist=False,
        cascade="all, delete-orphan"
    )