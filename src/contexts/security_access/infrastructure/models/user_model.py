import uuid

from sqlalchemy import UUID, Column, Integer, String, Boolean, DateTime
from datetime import datetime

from sqlalchemy.orm import relationship
from src.core.database import Base


class UserModel(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)    
    email = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=True)
    picture_url = Column(String, nullable=True)
    role = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    last_login = Column(DateTime, default=datetime.utcnow)
    refresh_tokens = relationship(
        "RefreshTokenModel", 
        back_populates="user", 
        cascade="all, delete-orphan"
    )