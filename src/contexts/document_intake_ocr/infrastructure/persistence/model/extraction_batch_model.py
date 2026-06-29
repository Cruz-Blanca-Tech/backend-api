# src/contexts/document_intake_ocr/infrastructure/persistence/models/batch_model.py
from uuid import UUID
from datetime import datetime
from typing import List
from sqlalchemy import ForeignKey, String, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.core.database import Base

class ExtractionBatchModel(Base):
    __tablename__ = "extraction_batches"
    
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    activity_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("activities.id"), nullable=False)
    created_by: Mapped[UUID] = mapped_column(UUID(as_uuid=True), nullable=False) # ID del usuario
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))    
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    
    documents: Mapped[List["DocumentItemModel"]] = relationship( # type: ignore
        "DocumentItemModel", 
        back_populates="batch", 
        cascade="all, delete-orphan", 
        lazy="selectin" # Evita el error de MissingGreenlet cargando el grafo de golpe
    )