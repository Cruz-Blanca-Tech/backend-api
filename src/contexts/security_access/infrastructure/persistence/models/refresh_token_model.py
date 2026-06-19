import uuid

from sqlalchemy import Column, String, DateTime, ForeignKey, UUID
from sqlalchemy.orm import relationship
from src.core.database import Base
# src/contexts/security_access/infrastructure/models/__init__.py
from src.contexts.security_access.infrastructure.persistence.models.user_model import UserModel

from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PG_UUID # Usa explícitamente el dialecto PG
import uuid

class RefreshTokenModel(Base):
    __tablename__ = "refresh_tokens"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    token_hash = Column(String(255), nullable=False, unique=True)
    expires_at = Column(DateTime, nullable=False)
    
    # Asegúrate de usar el mismo tipo UUID que en UserModel
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False) 
    
    user = relationship("UserModel", back_populates="refresh_tokens")