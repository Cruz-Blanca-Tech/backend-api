from pydantic import BaseModel
from uuid import UUID

from src.contexts.security_access.domain.value_objects.email import Email
from src.contexts.security_access.domain.value_objects.role import Role

class UpdateRoleRequest(BaseModel):
    role: Role

class UserResponse(BaseModel):
    id: UUID  # <--- Usa UUID aquí
    email: str
    role: Role
    full_name: str