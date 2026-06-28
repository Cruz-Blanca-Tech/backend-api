from dataclasses import dataclass
from typing import Any

@dataclass
class EnrichedField:
    name: str
    raw_value: Any
    normalized_value: Any

    @property
    def has_format_error(self) -> bool:
        """Devuelve True si existía un valor crudo (ej: detectado por OCR) pero no se pudo normalizar."""
        return bool(self.raw_value) and not self.normalized_value
    
    @property
    def is_valid(self) -> bool:
        """Devuelve True si el campo no tiene errores de formato."""
        return not self.has_format_error
