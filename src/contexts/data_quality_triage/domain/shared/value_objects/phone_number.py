import re
from dataclasses import dataclass

@dataclass(frozen=True)
class PhoneNumber:
    value: str

    _PATTERN = re.compile(r"^(?:\+?51)?(?:9\d{8}|(?:0?1)?[2-8]\d{6})$")

    @classmethod
    def is_valid(cls, phone_str: str) -> bool:
        """
        Valida si una cadena es un número de teléfono celular ordinario.
        Reglas: 9 dígitos comenzando con 9, opcionalmente con código de país (+51 o 51).
        """
        if not phone_str:
            return False
        clean = re.sub(r"[\s\-\(\)\.]", "", str(phone_str).strip())
        return bool(cls._PATTERN.match(clean))
