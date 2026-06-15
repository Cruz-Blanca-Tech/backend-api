from dataclasses import dataclass
from uuid import UUID, uuid4
from typing import List

@dataclass
class Program:
    """
    Entidad raíz que agrupa actividades relacionadas.
    Define el dominio operativo de la ONG (Ej. Programa Educa, Programa Salud).
    """
    id: UUID
    name: str
    description: str
    is_active: bool

    @classmethod
    def create(cls, name: str, description: str):
        return cls(
            id=uuid4(),
            name=name,
            description=description,
            is_active=True
        )