# src/contexts/auth/domain/entities/user.py
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import synonym
from src.contexts.security_access.domain.entities.authenticated_user import AuthenticatedUser
from src.contexts.security_access.domain.value_objects.email import InstitutionalEmail
from src.contexts.security_access.domain.value_objects.role import Role
from src.core.database import Base


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    
    _email = Column("email", String, unique=True, index=True, nullable=False)
    
    full_name = Column(String, nullable=True)
    picture_url = Column(String, nullable=True)  # <-- Añadido
    role = Column(String, default=Role.OPERATIVO, nullable=False)
    is_active = Column(Boolean, default=True)
    last_login = Column(DateTime, default=datetime.utcnow) # <-- Añadido

    @property
    def email(self):
        return InstitutionalEmail(self._email)

    @email.setter
    def email(self, value: InstitutionalEmail):
        self._email = str(value)

    email = synonym("_email", descriptor=email)

    def __init__(self, email: InstitutionalEmail, full_name: str, picture_url: str = None, role: Role = Role.OPERATIVO):
        self.email = email
        self.full_name = full_name
        self.picture_url = picture_url
        self.role = role

    @classmethod
    def create_new_user(cls, auth_data: AuthenticatedUser, allowed_domain: str = None):
        return cls(
            email=InstitutionalEmail(auth_data.email, allowed_domain=allowed_domain),
            full_name=auth_data.full_name,
            picture_url=auth_data.picture_url,
            role=Role.VISUALIZADOR 
        )
    
    def update_profile(self, auth_data: AuthenticatedUser):
            """
            Actualiza los datos del perfil y la fecha de última sesión.
            Esta es la única forma permitida para modificar estos campos.
            """
            self.full_name = auth_data.full_name
            self.picture_url = auth_data.picture_url
            self.last_login = datetime.utcnow()