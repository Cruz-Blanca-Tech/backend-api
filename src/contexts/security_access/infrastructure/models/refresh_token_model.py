import uuid

from sqlalchemy import Column, String, DateTime, ForeignKey, UUID
from sqlalchemy.orm import relationship
from src.core.database import Base
# src/contexts/security_access/infrastructure/models/__init__.py
from src.contexts.security_access.infrastructure.models.user_model import UserModel

class RefreshTokenModel(Base):
    __tablename__ = "refresh_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)    
    token_hash = Column(String(255), nullable=False, unique=True)
    expires_at = Column(DateTime, nullable=False)
    
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)    
    user = relationship("UserModel", back_populates="refresh_tokens")