from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID
from src.contexts.security_access.domain.value_objects.email import Email
from src.contexts.security_access.domain.value_objects.role import Role
from src.contexts.security_access.domain.entities.external_user_identity import ExternalUserIdentity

@dataclass
class User:
    id: UUID
    email: Email
    full_name: str
    role: Role
    picture_url: Optional[str] = None
    is_active: bool = True
    last_login: datetime = datetime.utcnow()

    @classmethod
    def create_new_user(cls, auth_data: ExternalUserIdentity) -> 'User':
        return cls(
            email=Email(auth_data.email),
            full_name=auth_data.full_name,
            picture_url=auth_data.picture_url,
            role=Role.VISUALIZADOR
        )

    def update_profile(self, auth_data: ExternalUserIdentity):
        self.full_name = auth_data.full_name
        self.picture_url = auth_data.picture_url
        self.last_login = datetime.utcnow()