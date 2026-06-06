from dataclasses import dataclass
from src.contexts.security_access.domain.value_objects.email import Email
from src.contexts.security_access.domain.value_objects.role import Role

@dataclass(frozen=True)
class TokenClaims:
    email: Email
    role: Role
    full_name: str

    def to_dict(self) -> dict:
        """Convierte los claims a un formato serializable para el JWT."""
        return {
            "sub": str(self.email),
            "role": str(self.role),
            "name": str(self.full_name)
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'TokenClaims':
        """Crea el VO a partir del payload del JWT."""
        return cls(
            email=Email(data.get("sub")),
            role=Role(data.get("role")),
            full_name= str(data.get("name"))
        )