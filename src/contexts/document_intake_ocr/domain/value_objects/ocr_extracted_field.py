from typing import Any
from dataclasses import dataclass, asdict

@dataclass(frozen=True)
class OcrExtractedField:
    """
    Value Object que representa un campo extraído por un motor de OCR.
    Encapsula el valor real y la certeza (confidence) de la inteligencia artificial.
    """
    value: Any
    confidence: float

    def to_dict(self) -> dict:
        """
        Serializa el objeto a diccionario para poder ser guardado en campos JSONB
        de SQLAlchemy de forma nativa.
        """
        return asdict(self)
