from __future__ import annotations
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import mapped_column, relationship
from src.core.database import Base


class DocumentCanonicalDataModel(Base):
    __tablename__ = "document_canonical_data"

    id = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    document_id = mapped_column(PG_UUID(as_uuid=True), ForeignKey("document_items.id"))

    data = mapped_column(JSONB, nullable=False)  # normalized + mapped

    schema_version = mapped_column(String(50), nullable=True)
    created_at = mapped_column(DateTime, default=datetime.utcnow)
    
    document = relationship("DocumentItemModel", back_populates="canonical_data")