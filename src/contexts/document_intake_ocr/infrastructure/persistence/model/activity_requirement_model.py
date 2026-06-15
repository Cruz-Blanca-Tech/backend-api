from __future__ import annotations
import uuid
from sqlalchemy import Float, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, declarative_base, relationship, mapped_column
from uuid import UUID, uuid4

from src.core.database import Base

class ActivityRequirementModel(Base):
    __tablename__ = "activity_requirements"
    
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    activity_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("activities.id"), nullable=False)
    
    # ID ajustado a UUID para consistencia con DocumentTypeConfig
    document_type_config_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("document_type_configs.id"), nullable=False)
    
    is_required: Mapped[bool] = mapped_column(Boolean, default=True)
    confidence_threshold: Mapped[float] = mapped_column(Float, default=0.85)
    
    # Referencias con strings para evitar el error de import circular
    activity: Mapped["ActivityModel"] = relationship("ActivityModel", back_populates="requirements") # type: ignore
    document_config: Mapped["DocumentTypeConfigModel"] = relationship("DocumentTypeConfigModel") # type: ignore