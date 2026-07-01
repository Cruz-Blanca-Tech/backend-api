import re
from dataclasses import dataclass

@dataclass(frozen=True)
class PhoneNumber:
    value: str

    _PATTERN = re.compile(r"^\+?[\d\s-]{7,15}$")

    @classmethod
    def is_valid(cls, phone_str: str) -> bool:
        """
        Valida matemáticamente si una cadena puede ser considerada un número de teléfono.
        Reglas: Entre 7 y 15 caracteres (dígitos, guiones o espacios) y puede iniciar con '+'.
        """
        if not phone_str:
            return False
        return bool(cls._PATTERN.match(phone_str.strip()))
