import re
from dataclasses import dataclass

@dataclass(frozen=True)
class Email:
    value: str
    ALLOWED_DOMAIN = "cruzblanca.org" # Define el dominio permitido aquí

    def __post_init__(self):
        # 1. Validación de formato básico
        if not re.match(r"[^@]+@[^@]+\.[^@]+", self.value):
            raise ValueError(f"El email '{self.value}' no tiene un formato válido.")
        
        # 2. Validación de dominio institucional
        if not self.value.endswith(f"@{self.ALLOWED_DOMAIN}"):
            raise ValueError(f"Solo se permiten correos del dominio @{self.ALLOWED_DOMAIN}")

    def __str__(self):
        return self.value