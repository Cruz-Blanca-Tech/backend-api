from dataclasses import dataclass
import re


@dataclass(frozen=True)
class DNI:
    """Value Object para garantizar que un DNI siempre sea válido."""
    value: str

    def __post_init__(self):
        if not re.match(r"^\d{8}$", self.value):
            raise ValueError(f"DNI '{self.value}' inválido: debe tener 8 dígitos numéricos.")