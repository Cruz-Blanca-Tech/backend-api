# src/contexts/auth/domain/entities/user.py
from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.orm import synonym
from src.contexts.security_access.domain.value_objects.email import Email
from src.contexts.security_access.domain.value_objects.role import Role
from src.core.database import Base


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    
    _email = Column("email", String, unique=True, index=True, nullable=False)
    
    full_name = Column(String, nullable=True)
    role = Column(String, default=Role.OPERATIVO, nullable=False)
    is_active = Column(Boolean, default=True)

    @property
    def email(self):
        return Email(self._email)

    @email.setter
    def email(self, value: Email):
        self._email = str(value)

    email = synonym("_email", descriptor=email)

    def __init__(self, email: Email, full_name: str, role: Role = Role.OPERATIVO):
        self.email = email
        self.full_name = full_name
        self.role = role