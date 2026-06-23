# src/contexts/document_intake_ocr/infrastructure/persistence/models/batch_model.py

from typing import Optional
from uuid import UUID as PyUUID
from datetime import datetime
from sqlalchemy import Float, ForeignKey, String, DateTime
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.core.database import Base  

class DocumentItemModel(Base):
    __tablename__ = "document_items"
    
    # Usamos PG_UUID para la BD y PyUUID para el tipado de Python
    id: Mapped[PyUUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    batch_id: Mapped[PyUUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("extraction_batches.id"), nullable=False)
    
    # =========================================================
    # NUEVOS CAMPOS DE TRAZABILIDAD (Agnósticos)
    # =========================================================
    # Aumentamos a 500 caracteres porque los URIs/URLs pueden ser muy largos
    source_id: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    custody_id: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    code: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    dni_reference: Mapped[str] = mapped_column(String(20), nullable=True)
    document_type_config_id: Mapped[PyUUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("document_type_configs.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    
    # SNAPSHOT PATTERN (JSONB): Aquí se escupe el resultado estructurado de Azure OCR
    extracted_data: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True) 
    confidence_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # Recuerda: Si el archivo es rechazado, se guarda en la BD con este motivo, no en RAM.
    failure_reason: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    batch: Mapped["ExtractionBatchModel"] = relationship("ExtractionBatchModel", back_populates="documents") # type: ignore