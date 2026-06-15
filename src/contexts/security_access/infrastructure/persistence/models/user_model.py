from uuid import UUID, uuid4
from typing import List, Optional
from datetime import datetime, timezone
from sqlalchemy import String, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.core.database import Base

class UserModel(Base):
    __tablename__ = "users"
    
    # id: Tipo Python (uuid.UUID) vs Columna (PG_UUID con as_uuid=True)
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    
    # Optional[str] porque es nullable=True
    full_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    picture_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    
    role: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Se recomienda datetime.now(timezone.utc) en lugar de datetime.utcnow (deprecado)
    last_login: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relación: Nota el uso de strings ("RefreshTokenModel") para evitar errores de import circular
    refresh_tokens: Mapped[List["RefreshTokenModel"]] = relationship( # type: ignore
        "RefreshTokenModel", 
        back_populates="user", 
        cascade="all, delete-orphan"
    )