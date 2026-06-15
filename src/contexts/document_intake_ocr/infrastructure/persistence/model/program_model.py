from __future__ import annotations

from typing import List, Optional
from uuid import UUID # Importa el tipo de Python
from sqlalchemy import String, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship, declarative_base
from sqlalchemy.dialects.postgresql import UUID as PG_UUID # Importa el dialecto SQL con alias
import datetime
from src.core.database import Base

class ProgramModel(Base):
    __tablename__ = "programs"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)    
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)

    activities: Mapped[List["ActivityModel"]] = relationship( # type: ignore
            "ActivityModel", 
            back_populates="program", 
            cascade="all, delete-orphan"
        )