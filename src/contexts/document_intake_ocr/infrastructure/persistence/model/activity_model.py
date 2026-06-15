from __future__ import annotations
from uuid import UUID, uuid4
import datetime
from typing import List
from sqlalchemy import String, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, declarative_base, relationship, mapped_column
from src.core.database import Base


class ActivityModel(Base):
    __tablename__ = "activities"
    
    # 1. Definición correcta del UUID con dialecto Postgres y auto-conversión
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    program_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("programs.id"), nullable=False)
    
    name: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)
    
    # 2. Relaciones usando strings para romper ciclos de importación
    program: Mapped["ProgramModel"] = relationship("ProgramModel", back_populates="activities") # type: ignore
    requirements: Mapped[List["ActivityRequirementModel"]] = relationship( # type: ignore
        "ActivityRequirementModel", back_populates="activity", cascade="all, delete-orphan"
    )