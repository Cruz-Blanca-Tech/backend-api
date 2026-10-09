from dataclasses import dataclass
import re

@dataclass(frozen=True)
class Phone:
    value: str

    def __post_init__(self):
        val = str(self.value).strip()
        if not val:
            raise ValueError("Phone cannot be empty")
        
        # Validar número de celular ordinario (9 dígitos empezando en 9, opcionalmente con prefijo +51 o 51)
        clean = re.sub(r"[\s\-\(\)\.]", "", val)
        if not re.match(r"^(?:\+?51)?9\d{8}$", clean):
            raise ValueError(f"Invalid phone format: {val}")
        
        # We need to bypass frozen to set the normalized value
        object.__setattr__(self, 'value', val)

    def __str__(self) -> str:
        return self.value
