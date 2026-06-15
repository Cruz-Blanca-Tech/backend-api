# src/contexts/document_intake/domain/value_objects.py
from enum import Enum
from typing import List

class SupportedMimeType(Enum):
    PDF = "application/pdf"
    JPEG = "image/jpeg"
    PNG = "image/png"

    @property
    def extension(self) -> str:
        """Propiedad que devuelve la extensión correspondiente al MimeType"""
        mapping = {
            self.PDF: "pdf",
            self.JPEG: "jpg",
            self.PNG: "png"
        }
        return mapping[self]

    @classmethod
    def get_supported_values(cls) -> List[str]:
        return [item.value for item in cls]

    @classmethod
    def validate(cls, mime_type: str) -> None:
        if mime_type not in cls.get_supported_values():
            raise ValueError(
                f"Tipo de archivo no soportado: '{mime_type}'. "
                f"Formatos permitidos: {', '.join(cls.get_supported_values())}"
            )