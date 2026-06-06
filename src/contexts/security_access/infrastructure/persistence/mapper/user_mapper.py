# src/contexts/security_access/infrastructure/mappers/user_mapper.py

from src.contexts.security_access.domain.entities.user import User
from src.contexts.security_access.infrastructure.persistence.models.user_model import UserModel
from src.contexts.security_access.domain.value_objects.email import Email
from src.contexts.security_access.domain.value_objects.role import Role

class UserMapper:
    @staticmethod
    def to_domain(user_model: UserModel) -> User:
        """Convierte de Modelo de BD a Entidad de Dominio"""
        return User(
            id=user_model.id,
            email=Email(user_model.email),
            full_name=user_model.full_name,
            picture_url=user_model.picture_url,
            role=Role(user_model.role),
            is_active=user_model.is_active,
            last_login=user_model.last_login
        )

    @staticmethod
    def to_infra(user_entity: User) -> UserModel:
        """Convierte de Entidad de Dominio a Modelo de BD"""
        return UserModel(
            id=user_entity.id,
            email=str(user_entity.email),
            full_name=user_entity.full_name,
            picture_url=user_entity.picture_url,
            role=str(user_entity.role),
            is_active=user_entity.is_active,
            last_login=user_entity.last_login
        )